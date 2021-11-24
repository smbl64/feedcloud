import datetime
import logging
import time
from typing import List

import sqlalchemy as sa

from feedcloud import database, settings
from feedcloud.database import Feed, FeedUpdateRun

from . import tasks

logger = logging.getLogger("feedcloud.Scheduler")


class Scheduler:
    """
    Scheduler periodically finds feeds that need to be updated and
    schedules them for download.

    The actual download happens through the async workers in the background.
    """

    def run_forever(self):
        while True:
            try:
                self.run_once()
            except Exception:
                logger.exception("Scheduling failed.")

            time.sleep(settings.TASK_SCHEDULER_INTERVAL_SECONDS)

    def run_once(self):
        logger.info("Going to pick up feeds...")
        feeds = self.find_feeds()
        logger.info(f"Found {len(feeds)} feed(s).")

        for feed in feeds:
            tasks.download_feed.send(feed.id)

    def find_feeds(self) -> List[Feed]:
        """
        Find feeds that are ready to be downloaded.

        This uses a LATERAL JOIN to find the last FeedUpdateRun for each
        feed and check the values there.
        """
        with database.get_session() as session:
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
            #    a failed one which has a schedule date before 'now'
            query = (
                session.query(Feed, last_run)
                .outerjoin(last_run, Feed.id == last_run.c.feed_id)
                .filter(
                    sa.or_(
                        last_run.c.id == None,  # noqa  ('is None' won't work here)
                        last_run.c.status != FeedUpdateRun.FAILED,
                        sa.and_(
                            last_run.c.status == FeedUpdateRun.FAILED,
                            last_run.c.next_run_schedule
                            != None,  # noqa (Same with None)
                            last_run.c.next_run_schedule < datetime.datetime.now(),
                        ),
                    )
                )
            )

            return [row[0] for row in query.all()]


if __name__ == "__main__":
    scheduler = Scheduler()
    scheduler.run_forever()
