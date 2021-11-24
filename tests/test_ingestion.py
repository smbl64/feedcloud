import datetime
import pathlib
import time
from typing import Iterable

import pytest

import feedcloud.ingest.worker
from feedcloud import settings
from feedcloud.api import services
from feedcloud.database import Entry, Feed, FeedUpdateRun
from feedcloud.ingest import parser
from feedcloud.ingest.scheduler import Scheduler
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
    feed = Feed(url="bla", user_id=test_user.id)
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

    db_entries = db_session.query(Entry).all()
    assert len(db_entries) == 1

    runs = db_session.query(FeedUpdateRun).all()
    assert len(runs) == 1
    assert runs[0].status == FeedUpdateRun.SUCCESS


def test_worker_avoids_duplicates(db_session, test_user):
    feed = Feed(url="bla", user_id=test_user.id)
    db_session.add(feed)
    db_session.flush()

    entry = Entry(
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

    db_entries = db_session.query(Entry).all()
    assert len(db_entries) == 1


def get_test_xml_file_path() -> str:
    xml_file = pathlib.Path(__file__).parent / "rss_feed.xml"
    file_path = str(xml_file.absolute())
    return file_path


def test_feed_parser_returns_items():
    """
    Parse the sample RSS file.
    This file is taken from: https://lorem-rss.herokuapp.com/feed
    """
    file_path = get_test_xml_file_path()

    # Note: `download_entries` uses the `feedparser` package which can
    # parse strings as well. But here we will pass the file path to
    # be more similar to a URL.
    entries = parser.download_entries(file_path)
    assert len(entries) == 2


def test_feed_parses_reports_failures():
    with pytest.raises(parser.ParseError):
        parser.download_entries("http://some-invalid-url:23232")


def test_worker_saves_failed_feed_runs(db_session, test_user):
    feed = Feed(url="http://invalid-url:2323", user_id=test_user.id)
    db_session.add(feed)
    db_session.commit()

    # This variable and function will be used to see if
    # the worker sends failure notification to the user!
    notification_feed_id = None

    def failure_notifier(feed_id):
        nonlocal notification_feed_id
        notification_feed_id = feed_id

    worker = FeedWorker(feed, parser.download_entries, failure_notifier=failure_notifier)
    for _ in range(settings.FEED_MAX_FAILURE_COUNT):
        worker.start()

    runs = db_session.query(FeedUpdateRun).order_by(FeedUpdateRun.timestamp).all()
    assert len(runs) == 3
    assert runs[-1].next_run_schedule is None
    assert [r.failure_count for r in runs] == [1, 2, 3]
    assert notification_feed_id == feed.id


def test_scheduler_picks_correct_feeds(db_session, test_user):
    not_run_feed = Feed(url="not_run", user_id=test_user.id)
    successful_feed = Feed(url="successful", user_id=test_user.id)
    once_failed_feed = Feed(url="once_failed", user_id=test_user.id)
    totally_failed_feed = Feed(url="totally_failed", user_id=test_user.id)
    db_session.add_all(
        [not_run_feed, successful_feed, once_failed_feed, totally_failed_feed]
    )
    db_session.flush()

    # Successful feed
    db_session.add(
        FeedUpdateRun(
            feed_id=successful_feed.id,
            timestamp=datetime.datetime.now(),
            status=FeedUpdateRun.SUCCESS,
            failure_count=0,
        )
    )

    # Once-failed feed
    db_session.add(
        FeedUpdateRun(
            feed_id=once_failed_feed.id,
            timestamp=datetime.datetime.now() - datetime.timedelta(hours=2),
            next_run_schedule=datetime.datetime.now() - datetime.timedelta(hours=1),
            status=FeedUpdateRun.FAILED,
            failure_count=1,
        )
    )

    # Totally-failed feed
    for i in range(settings.FEED_MAX_FAILURE_COUNT):
        # Each run should have a close timestamp
        hours = settings.FEED_MAX_FAILURE_COUNT - i

        next_run_schedule = datetime.datetime.now() - datetime.timedelta(hours=hours)
        if i == settings.FEED_MAX_FAILURE_COUNT - 1:
            next_run_schedule = None

        db_session.add(
            FeedUpdateRun(
                feed_id=totally_failed_feed.id,
                timestamp=datetime.datetime.now() - datetime.timedelta(hours=hours),
                next_run_schedule=next_run_schedule,
                status=FeedUpdateRun.FAILED,
                failure_count=i + 1,
            )
        )

    db_session.commit()

    scheduler = Scheduler()
    feeds = scheduler.find_feeds()
    assert {f.id for f in feeds} == {
        not_run_feed.id,
        successful_feed.id,
        once_failed_feed.id,
    }


def test_simulate_backoff_mechanism(
    monkeypatch, db_session, client, test_user, broker, stub_worker
):
    feed = Feed(url="http://invalid-url:2323", user_id=test_user.id)
    db_session.add(feed)
    db_session.commit()

    def fast_next_run_calc(failure_count: int, max_failure_count: int, **kwargs):
        """
        A faster alternative to the backoff calculator in the worker.
        """
        if failure_count >= max_failure_count:
            return None

        return datetime.datetime.now() + datetime.timedelta(
            milliseconds=100 * failure_count
        )

    # Since waiting for seconds and minutes for the exponential backoff in a
    # test is not feasible, we monkeypatch the logic and use milliseconds.
    monkeypatch.setattr(
        feedcloud.ingest.worker, "calculate_next_run_time", fast_next_run_calc
    )

    scheduler = Scheduler()

    for _ in range(settings.FEED_MAX_FAILURE_COUNT):
        scheduler.run_once()
        broker.join("default")
        stub_worker.join()
        time.sleep(0.5)

    max_runs = settings.FEED_MAX_FAILURE_COUNT
    assert db_session.query(FeedUpdateRun).count() == max_runs

    # Let's run the scheduler one more time. Since this feed is permanently failed,
    # we expect to see no more FeedUpdateRuns
    scheduler.run_once()
    broker.join("default")
    stub_worker.join()
    assert db_session.query(FeedUpdateRun).count() == max_runs

    # Now let's fix the feed and do a force-update. After a successful run, scheduler
    # must schedule the feed again.
    feed.url = get_test_xml_file_path()
    db_session.add(feed)
    db_session.commit()

    services.force_run_feed(test_user.username, feed.id)
    broker.join("default")
    stub_worker.join()
    assert db_session.query(FeedUpdateRun).count() == max_runs + 1

    # See if scheduler re-schedules the feed
    scheduler.run_once()
    broker.join("default")
    stub_worker.join()
    assert db_session.query(FeedUpdateRun).count() == max_runs + 2
