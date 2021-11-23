import dramatiq
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from feedcloud import settings


@dramatiq.actor
def download_feed_entries():
    pass


def start_scheduler():
    scheduler = BlockingScheduler()
    scheduler.add_job(
        download_feed_entries.send,
        CronTrigger.from_crontab(settings.TASK_SCHEDULER_CRONTAB),
    )

    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    start_scheduler()
