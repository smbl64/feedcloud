from typing import List

import feedparser

from .types import FeedEntry


def download_entries(url: str) -> List[FeedEntry]:
    result = feedparser.parse(url)
    if result.bozo:
        raise ParseError(f"Failed to read the feed: {str(result.bozo_exception)}")

    return result.entries


class ParseError(Exception):
    pass
