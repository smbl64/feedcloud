import logging

import dramatiq

from feedcloud import database
from feedcloud.database import Feed

from .parser import download_entries
from .worker import FeedWorker

logger = logging.getLogger(__name__)


# Setting max_retries to zero because FeedWorker and the Scheduler have
# their own retry mechanism.
@dramatiq.actor(max_retries=0)
def download_feed(feed_id):
    logger.info(f"Downloading feed {feed_id}")
    with database.get_session() as session:
        feed = session.query(Feed).filter(Feed.id == feed_id).one_or_none()
        if not feed:
            logger.warn(f"Feed not found: feed_id={feed_id}")
            return

        worker = FeedWorker(feed, downloader=download_entries)
        worker.start()
