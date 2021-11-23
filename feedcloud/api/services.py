from typing import List, Optional

import sqlalchemy.orm

from feedcloud import database, helpers
from feedcloud.database import Entry, Feed, User

from . import exceptions


def find_user(username: str, session: sqlalchemy.orm.Session) -> Optional[User]:
    return session.query(User).filter(User.username == username).one_or_none()


def authenticate_user(username: str, password: str) -> bool:
    with database.get_session() as session:
        user = find_user(username, session)
        if not user:
            return False

        return helpers.check_password(password, user.password_hash)


def register_feed(username: str, url: str) -> bool:
    with database.get_session() as session:
        user = find_user(username, session)
        if not user:
            raise exceptions.AuthorizationFailedError("User not found")

        feed = (
            session.query(Feed)
            .filter(Feed.url == url, Feed.user_id == user.id)
            .one_or_none()
        )

        if feed:
            return False

        feed = Feed(url=url, user_id=user.id)
        session.add(feed)
        session.commit()
        return True


def unregister_feed(username: str, url: str) -> bool:
    with database.get_session() as session:
        user = find_user(username, session)
        if not user:
            raise exceptions.AuthorizationFailedError("User not found")

        feed = (
            session.query(Feed)
            .filter(Feed.url == url, Feed.user_id == user.id)
            .one_or_none()
        )

        if not feed:
            return False

        session.delete(feed)
        session.commit()
        return True


def get_feeds(username: str) -> List[Feed]:
    with database.get_session() as session:
        user = find_user(username, session)
        if not user:
            raise exceptions.AuthorizationFailedError("User not found")

        feeds = (
            session.query(Feed)
            .filter(Feed.user_id == user.id)
            .all()
        )

        return feeds
