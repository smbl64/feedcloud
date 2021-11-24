import logging

import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker

from feedcloud import database, settings
from feedcloud.database import Feed

from .parser import download_entries
from .worker import FeedWorker

logger = logging.getLogger("feedcloud.Tasks")

rabbitmq_broker = RabbitmqBroker(url=settings.BROKER_URL)
dramatiq.set_broker(rabbitmq_broker)


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

    logger.info(f"Finished processing feed {feed_id}")
