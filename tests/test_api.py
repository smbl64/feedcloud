import datetime

import flask

from feedcloud import database


def test_authenticate_user(client, test_user):
    url = flask.url_for("authenticate")
    # Try with a non-existing user
    resp = client.post(
        url,
        json=dict(username="I don't exist", password="invalid password"),
    )
    assert resp.status_code == 401

    # Try with a invalid password
    resp = client.post(
        url,
        json=dict(username=test_user.username, password="invalid password"),
    )
    assert resp.status_code == 401

    resp = client.post(
        url,
        json=dict(username=test_user.username, password="test"),
    )
    assert resp.status_code == 200
    assert "token" in resp.json


def authenticate(client, user):
    url = flask.url_for("authenticate")
    resp = client.post(
        url,
        json=dict(username=user.username, password="test"),
    )
    assert resp.status_code == 200
    token = resp.json["token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_feed(db_session, client, test_user):
    headers = authenticate(client, test_user)

    url = flask.url_for("register_feed")
    resp = client.post(url, json=dict(url="http://bla"), headers=headers)
    assert resp.status_code == 201

    # Register it for a second time
    resp = client.post(url, json=dict(url="http://bla"), headers=headers)
    assert resp.status_code == 409

    feeds = db_session.query(database.Feed).all()
    assert len(feeds) == 1
    assert feeds[0].url == "http://bla"


def test_unregister_feed(db_session, client, test_user):
    headers = authenticate(client, test_user)

    # 404; Feed doesn't exist yet
    url = flask.url_for("unregister_feed")
    resp = client.delete(url, json=dict(url="http://bla"), headers=headers)
    assert resp.status_code == 404

    # Create the feed
    db_session.add(database.Feed(user_id=test_user.id, url="http://bla"))
    db_session.commit()

    # Try again
    resp = client.delete(url, json=dict(url="http://bla"), headers=headers)
    assert resp.status_code == 200
    assert db_session.query(database.Feed).count() == 0


def test_get_feeds(db_session, client, test_user):
    another_user = database.User(username="another", password_hash="...")
    db_session.add(another_user)
    db_session.commit()

    headers = authenticate(client, test_user)

    # Create some feeds
    db_session.add_all(
        [
            database.Feed(user_id=test_user.id, url="user-1-feed-1"),
            database.Feed(user_id=test_user.id, url="user-1-feed-2"),
            database.Feed(user_id=another_user.id, url="user-2-feed-1"),
        ]
    )
    db_session.commit()

    url = flask.url_for("get_feeds")
    resp = client.get(url, headers=headers)
    assert resp.status_code == 200
    response_urls = {f["url"] for f in resp.json["feeds"]}
    assert response_urls == {"user-1-feed-1", "user-1-feed-2"}


def test_list_entries_for_a_feed(db_session, client, test_user):
    headers = authenticate(client, test_user)

    # Create some feeds
    feed1 = database.Feed(user_id=test_user.id, url="feed-1")
    feed2 = database.Feed(user_id=test_user.id, url="feed-2")
    db_session.add_all([feed1, feed2])
    db_session.flush()

    # Create some entries for those two feeds
    entry_data = [
        ("entry 1", feed1.id),
        ("entry 2", feed1.id),
        ("entry 3", feed2.id),
        ("entry 4", feed2.id),
    ]
    start_dt = datetime.datetime.now() - datetime.timedelta(days=1)

    for idx, (title, feed_id) in enumerate(entry_data):
        # Each entry is published 1 hour after the previous one
        entry_date = start_dt + datetime.timedelta(hours=idx)

        entry = database.Entry(
            title=title,
            feed_id=feed_id,
            published_at=entry_date,
            original_id="e-" + str(idx),
            summary="",
            link="",
        )
        db_session.add(entry)

    db_session.commit()

    # Fetch entries for feed 1
    url = flask.url_for("get_feed_entries", feed_id=feed1.id)
    resp = client.get(url, headers=headers)
    assert resp.status_code == 200

    # Make sure that we get the entries for feed 1 in descending order by published date
    titles = [e["title"] for e in resp.json["entries"]]
    assert titles == ["entry 2", "entry 1"]


def test_filter_feed_entries_by_status(db_session, client, test_user):
    headers = authenticate(client, test_user)

    # Create the feed
    feed = database.Feed(user_id=test_user.id, url="feed-1")
    db_session.add(feed)
    db_session.flush()

    # Create some entries for those two feeds
    entry_data = [
        ("entry 1", "read"),
        ("entry 2", "read"),
        ("entry 3", "unread"),
        ("entry 4", "unread"),
    ]
    start_dt = datetime.datetime.now() - datetime.timedelta(days=1)

    for idx, (title, status) in enumerate(entry_data):
        # Each entry is published 1 hour after the previous one
        entry_date = start_dt + datetime.timedelta(hours=idx)

        entry = database.Entry(
            title=title,
            feed_id=feed.id,
            published_at=entry_date,
            original_id="some-id" + str(idx),
            summary="",
            link="",
            status=status,
        )
        db_session.add(entry)

    db_session.commit()

    # Fetch "read" entries for feed 1
    url = flask.url_for("get_feed_entries", feed_id=feed.id, status="read")
    resp = client.get(url, headers=headers)
    assert resp.status_code == 200
    titles = {e["title"] for e in resp.json["entries"]}
    assert titles == {"entry 1", "entry 2"}

    # Fetch "unread" entries for feed 1
    url = flask.url_for("get_feed_entries", feed_id=feed.id, status="unread")
    resp = client.get(url, headers=headers)
    assert resp.status_code == 200
    titles = {e["title"] for e in resp.json["entries"]}
    assert titles == {"entry 3", "entry 4"}


def test_change_entry_status(db_session, client, test_user):
    another_user = database.User(username="another", password_hash="...")
    db_session.add(another_user)
    db_session.commit()

    headers = authenticate(client, test_user)

    # Create some feeds
    feed = database.Feed(user_id=test_user.id, url="feed")
    feed_another_user = database.Feed(user_id=another_user.id, url="feed-another-user")
    db_session.add_all([feed, feed_another_user])
    db_session.flush()

    # Create some entries for those two feeds
    target_entry = database.Entry(
        title="target entry",
        feed_id=feed.id,
        published_at=datetime.datetime.now(),
        original_id="e-1",
        summary="",
        link="",
    )
    unaccessible_entry = database.Entry(
        title="unaccessible entry",
        feed_id=feed_another_user.id,  # <- belongs to another user
        published_at=datetime.datetime.now(),
        original_id="e-2",
        summary="",
        link="",
    )
    db_session.add_all([target_entry, unaccessible_entry])
    db_session.commit()

    # User doesn't have access to this entry
    url = flask.url_for("change_entry_status", entry_id=unaccessible_entry.id)
    resp = client.put(url, json={"status": "read"}, headers=headers)
    assert resp.status_code == 404

    # User can mark her own entry as 'read'
    url = flask.url_for("change_entry_status", entry_id=target_entry.id)
    resp = client.put(url, json={"status": "read"}, headers=headers)
    assert resp.status_code == 200

    db_session.refresh(target_entry)
    assert target_entry.status == "read"

    # User can change the status back to 'unread'
    url = flask.url_for("change_entry_status", entry_id=target_entry.id)
    resp = client.put(url, json={"status": "unread"}, headers=headers)
    assert resp.status_code == 200

    db_session.refresh(target_entry)
    assert target_entry.status == "unread"


def test_get_all_entries(db_session, client, test_user):
    headers = authenticate(client, test_user)

    # Create some feeds
    feed1 = database.Feed(user_id=test_user.id, url="feed-1")
    feed2 = database.Feed(user_id=test_user.id, url="feed-2")
    db_session.add_all([feed1, feed2])
    db_session.flush()

    # Create some entries for those two feeds
    entry_data = [
        ("entry 1", feed1.id, "read"),
        ("entry 2", feed1.id, "unread"),
        ("entry 3", feed2.id, "read"),
        ("entry 4", feed2.id, "unread"),
    ]
    start_dt = datetime.datetime.now() - datetime.timedelta(days=1)

    for idx, (title, feed_id, status) in enumerate(entry_data):
        # Each entry is published 1 hour after the previous one
        entry_date = start_dt + datetime.timedelta(hours=idx)

        entry = database.Entry(
            title=title,
            feed_id=feed_id,
            published_at=entry_date,
            original_id="e-" + str(idx),
            summary="",
            link="",
            status=status,
        )
        db_session.add(entry)

    db_session.commit()

    test_table = [
        ("read", ["entry 3", "entry 1"]),
        ("unread", ["entry 4", "entry 2"]),
        (None, ["entry 4", "entry 3", "entry 2", "entry 1"]),
    ]

    for status, expected_titles in test_table:
        url = flask.url_for("get_entries", status=status)
        resp = client.get(url, headers=headers)
        assert resp.status_code == 200
        titles = [e["title"] for e in resp.json["entries"]]
        assert titles == expected_titles
