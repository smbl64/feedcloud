import logging

import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.brokers.stub import StubBroker

from feedcloud import database, settings
from feedcloud.database import Feed

from .parser import download_entries
from .worker import FeedWorker

logger = logging.getLogger("feedcloud.Tasks")


if settings.IS_TESTING:
    broker = StubBroker(middleware=[])
    broker.emit_after("process_boot")
    dramatiq.set_broker(broker)
else:
    logger.info("Using RabbitMQ broker")
    broker = RabbitmqBroker(url=settings.BROKER_URL)
    dramatiq.set_broker(broker)


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

        worker = FeedWorker(
            feed,
            downloader=download_entries,
            failure_notifier=notify_user_on_failure.send,
        )
        worker.start()

    logger.info(f"Finished processing feed {feed_id}")


@dramatiq.actor(max_retries=3)
def notify_user_on_failure(feed_id):
    """
    Simulate sending a notification to user about feed failure.
    """
    logger.info("Feed {feed_id} failed. Notifying user...")
