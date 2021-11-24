from typing import Any, List

import feedparser


class FeedParser:
    def __init__(self, url: str):
        self.url = url

    def get_entries(self) -> List[Any]:
        result = feedparser.parse(self.url)
        if result.bozo:
            raise ParseError(f"Failed to read the feed: {str(result.bozo_exception)}")

        return result.entries


class ParseError(Exception):
    pass
