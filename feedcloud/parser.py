from typing import Any, Dict, List

import feedparser


class FeedParser:
    def __init__(self, url: str):
        self.url = url

    def get_entries(self) -> Any:
        result = feedparser.parse(self.url)
        return result.entries
