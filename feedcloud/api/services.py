from typing import List, Optional

import sqlalchemy.orm

from feedcloud import database, helpers
from feedcloud.database import Entry, Feed, User

from . import exceptions


def find_user(
    username: str, session: sqlalchemy.orm.Session, raise_error_if_missing: bool = True
) -> Optional[User]:
    user = session.query(User).filter(User.username == username).one_or_none()
    if not user and raise_error_if_missing:
        raise exceptions.AuthorizationFailedError("User not found")

    return user


def authenticate_user(username: str, password: str) -> bool:
    with database.get_session() as session:
        user = find_user(username, session, raise_error_if_missing=False)
        if not user:
            return False

        return helpers.check_password(password, user.password_hash)


def register_feed(username: str, url: str) -> bool:
    with database.get_session() as session:
        user = find_user(username, session)

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


def get_entries(
    username: str, *, feed_id: Optional[int] = None, entry_status: Optional[str] = None
) -> List[Entry]:
    if entry_status and entry_status not in database.Entry.STATUS_LIST:
        raise ValueError(f"Invalid status: {entry_status}")

    with database.get_session() as session:
        user = find_user(username, session)

        query = (
            session.query(Entry)
            .join(Feed, Entry.feed_id == Feed.id)
            .filter(Feed.user_id == user.id)
            .order_by(Entry.published_at.desc())
        )

        if feed_id:
            query = query.filter(Feed.id == feed_id)

        if entry_status:
            query = query.filter(Entry.status == entry_status)

        return query.all()


def change_entry_status(username: str, entry_id: int, new_status: str) -> bool:
    with database.get_session() as session:
        user = find_user(username, session)

        entry = (
            session.query(Entry)
            .join(Feed, Entry.feed_id == Feed.id)
            .filter(Feed.user_id == user.id, Entry.id == entry_id)
            .one_or_none()
        )

        if not entry:
            return False

        entry.status = new_status
        session.commit()
        return True
