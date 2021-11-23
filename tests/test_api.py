import flask

from feedcloud import database, helpers


def test_auth(db_session, client):

    with database.get_session() as session:
        hash = helpers.hash_password("test")
        user = database.User(username="test", password_hash=hash)
        session.add(user)
        session.commit()

    url = flask.url_for("authenticate")
    resp = client.post(
        url,
        json=dict(username="test", password="invalid password"),
    )
    assert resp.status_code == 401

    resp = client.post(
        url,
        json=dict(username="test", password="test"),
    )
    assert resp.status_code == 200
    assert "token" in resp.json
