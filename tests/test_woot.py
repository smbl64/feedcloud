from feedcloud import database


def test_stuff(db_session):
    user = database.User(username="mo", password_hash="232")
    db_session.add(user)
    db_session.flush()

    feed = database.Feed(url="bla", user_id=user.id)
    db_session.add(feed)
    db_session.flush()

    entry = database.Entry(title="hi", summary="How are you", feed_id=feed.id)
    db_session.add(entry)
    db_session.commit()
