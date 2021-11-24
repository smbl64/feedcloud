import datetime
import logging
import time
from typing import Any, List, Optional

import sqlalchemy.orm

from feedcloud import database, settings
from feedcloud.parser import FeedParser, ParseError

logger = logging.getLogger(__name__)


class FeedWorker:
    """
    FeedWorker downloads the entries for a feed and saves them in the database.
    It will also schedule the next run for a feed if required.
    """
    def __init__(self, feed: database.Feed):
        self.feed = feed

    def start(self):
        parser = FeedParser(self.feed.url)
        with database.get_session() as session:
            try:
                entries = parser.get_entries()
            except ParseError:
                logger.exception("Failed to read entries from the feed")
                self._save_failure_run(session)
                session.commit()
                return

            self.save_entries(session, entries)
            session.commit()

    def save_entries(self, session: sqlalchemy.orm.Session, entries: List[Any]) -> None:
        n_downloaded = 0
        n_ignored = 0

        for entry_dict in entries:
            if self.does_entry_exist(session, entry_dict.id):
                n_ignored += 1
                continue

            published_date = self._make_datetime(entry_dict.published_parsed)
            entry = database.Entry(
                feed_id=self.feed.id,
                original_id=entry_dict.id,
                title=entry_dict.title,
                summary=entry_dict.description,
                link=entry_dict.link,
                published_at=published_date
            )
            session.add(entry)
            n_downloaded += 1

        self._save_success_run(
            session,
            n_downloaded=n_downloaded,
            n_ignored=n_ignored,
        )

    def _save_success_run(
        self,
        session: sqlalchemy.orm.Session,
        *,
        n_downloaded: int,
        n_ignored: int
    ) -> None:
        feed_update = database.FeedUpdateRun(
            feed_id=self.feed.id,
            timestamp=datetime.datetime.now(),
            n_downloaded=n_downloaded,
            n_ignored=n_ignored,
            status=database.FeedUpdateRun.SUCCESS,
        )
        session.add(feed_update)

    def _save_failure_run(
        self,
        session: sqlalchemy.orm.Session,
    ) -> None:
        FeedUpdateRun = database.FeedUpdateRun

        # Find the last run
        last_run = (
            session.query(FeedUpdateRun)
            .filter(FeedUpdateRun.feed_id == self.feed.id)
            .order_by(FeedUpdateRun.timestamp.desc())
            .first()
        )

        if last_run is None or last_run.status != FeedUpdateRun.FAILED:
            failure_count = 1
        else:
            failure_count = last_run.failure_count + 1

        next_run_dt = calculate_next_run_time(
            failure_count, settings.FEED_MAX_FAILURE_COUNT
        )

        run = FeedUpdateRun(
            feed_id=self.feed.id,
            failure_count=failure_count,
            timestamp=datetime.datetime.now(),
            status=FeedUpdateRun.FAILED,
            next_run_schedule=next_run_dt,
        )
        session.add(run)

    def _make_datetime(self, dt_tuple: tuple) -> datetime.datetime:
        """
        Convert a datetime-tuple to a Python datetime.
        """
        return datetime.datetime.fromtimestamp(time.mktime(dt_tuple))

    def does_entry_exist(self, session: sqlalchemy.orm.Session, entry_id: str) -> bool:
        count = (
            session.query(database.Entry)
            .filter(database.Entry.original_id == entry_id)
            .count()
        )

        return count != 0


def calculate_next_run_time(
    failure_count: int,
    max_failure_count: int,
    *,
    min_seconds: int = 5,
    multiplier: int = 10,
    max_seconds: int = 3600,
) -> Optional[datetime.datetime]:
    """
    Calculate the next running time using a exponential backoff formula.
    """
    seconds = None
    if failure_count < max_failure_count:
        seconds = min(min_seconds + multiplier * 2 ** failure_count, max_seconds)

    if seconds:
        return datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    else:
        return None
