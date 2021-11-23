import flask

from feedcloud import database, helpers


def test_auth(db_session, client, test_user):
    url = flask.url_for("authenticate")
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
