import datetime
import logging
import time
from typing import List

import sqlalchemy as sa

from feedcloud import database, settings, tasks
from feedcloud.database import Feed, FeedUpdateRun

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, sleep_duration: int = 3600):
        self.sleep_duration = sleep_duration

    def start(self):
        while True:
            feeds = self.find_feeds()
            for feed in feeds:
                tasks.download_feed.send(feed.id)

            time.sleep(self.sleep_duration)

    def find_feeds(self) -> List[Feed]:
        """
        Find feeds that are ready to be downloaded.

        This uses a LATERAL JOIN to find the last FeedUpdateRun for each
        feed and check the values there.
        """
        session = database.get_session()
        last_run_subq = (
            session.query(FeedUpdateRun)
            .filter(FeedUpdateRun.feed_id == Feed.id)
            .order_by(FeedUpdateRun.timestamp.desc())
            .limit(1)
            .subquery()
            .lateral()
        )

        last_run = sa.alias(last_run_subq, "last_run")

        # For each feed:
        #    There should be no last run OR
        #    a successful last run OR
        #    a failed one which has a schedule date before now
        query = (
            session.query(Feed, last_run)
            .outerjoin(last_run, Feed.id == last_run.c.feed_id)
            .filter(
                sa.or_(
                    last_run.c.id == None,  # noqa  ('is None' won't work here)
                    last_run.c.status != FeedUpdateRun.FAILED,
                    sa.and_(
                        last_run.c.status == FeedUpdateRun.FAILED,
                        last_run.c.next_run_schedule < datetime.datetime.now(),
                    ),
                )
            )
        )

        return [row[0] for row in query.all()]


if __name__ == "__main__":
    scheduler = Scheduler()
    scheduler.start()
