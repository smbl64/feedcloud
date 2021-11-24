import datetime
from typing import Iterable

from feedcloud import database
from feedcloud.ingest.types import FeedEntry
from feedcloud.ingest.worker import FeedWorker


class FakeDownloader:
    """
    A simple feed downloader which returns the given entries when the object is called.
    """
    def __init__(self, entries: Iterable[FeedEntry]):
        self.entries = entries

    def __call__(self, *args):
        return self.entries


def make_time_tuple(dt: datetime.datetime) -> tuple:
    return dt.timetuple()


def test_worker_saves_entries(db_session, test_user):
    feed = database.Feed(url="bla", user_id=test_user.id)
    db_session.add(feed)
    db_session.commit()

    entries = [
        FeedEntry(
            id="entry-1",
            title="",
            description="",
            link="http://feed/1",
            published_parsed=make_time_tuple(datetime.datetime(2021, 11, 24, 10, 0, 0)),
        )
    ]

    downloader = FakeDownloader(entries)
    worker = FeedWorker(feed, downloader)
    worker.start()

    db_entries = db_session.query(database.Entry).all()
    assert len(db_entries) == 1


def test_worker_avoids_duplicates(db_session, test_user):
    feed = database.Feed(url="bla", user_id=test_user.id)
    db_session.add(feed)
    db_session.flush()

    entry = database.Entry(
        feed_id=feed.id,
        original_id="unique-id",
        title="",
        summary="",
        link="",
        published_at=datetime.datetime.now(),
    )
    db_session.add(entry)
    db_session.commit()

    entries = [
        FeedEntry(
            id="unique-id",  # Same ID as original_id above
            title="",
            description="",
            link="http://feed/1",
            published_parsed=make_time_tuple(datetime.datetime(2021, 11, 24, 10, 0, 0)),
        )
    ]

    downloader = FakeDownloader(entries)
    worker = FeedWorker(feed, downloader)
    worker.start()

    db_entries = db_session.query(database.Entry).all()
    assert len(db_entries) == 1
