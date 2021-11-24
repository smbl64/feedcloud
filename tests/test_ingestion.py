import datetime
import pathlib
from typing import Iterable

import pytest

from feedcloud import database
from feedcloud.ingest import parser
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


def test_feed_parser_returns_items():
    """
    Parse the sample RSS file.
    This file is taken from: https://lorem-rss.herokuapp.com/feed
    """
    xml_file = pathlib.Path(__file__).parent / "rss_feed.xml"
    file_path = str(xml_file.absolute())

    # Note: `download_entries` uses the `feedparser` package which can
    # parse strings as well. But here we will pass the file path to
    # be more similar to a URL.
    entries = parser.download_entries(file_path)
    assert len(entries) == 2


def test_feed_parses_reports_failures():
    with pytest.raises(parser.ParseError):
        parser.download_entries("http://some-invalid-url:23232")
