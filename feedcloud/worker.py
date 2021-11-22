from typing import Any

import sqlalchemy.orm

from feedcloud import database
from feedcloud.parser import FeedParser


class FeedWorker:
    def __init__(self, feed: database.Feed):
        self.feed = feed

    def start(self):
        parser = FeedParser(self.feed.url)
        entries = parser.get_entries()
        self.save_entries(entries)

    def save_entries(self, entries: Any) -> None:
        with database.get_session() as session:
            for entry_dict in entries:
                if self.does_entry_exist(session, entry_dict.id):
                    continue

                entry = database.Entry(
                    feed_id=self.feed.id,
                    original_id=entry_dict.id,
                    title=entry_dict.title,
                    summary=entry_dict.description,
                    link=entry_dict.link,
                )
                session.add(entry)

            session.commit()

    def does_entry_exist(self, session: sqlalchemy.orm.Session, entry_id: str) -> bool:
        count = (
            session.query(database.Entry)
            .filter(database.Entry.original_id == entry_id)
            .count()
        )

        return count != 0
