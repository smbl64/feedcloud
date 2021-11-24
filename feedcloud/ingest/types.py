from collections import namedtuple
from typing import Callable, Iterable

# A simple namedtuple representing the important fields
# in a feed entry.
FeedEntry = namedtuple("Entry", "id title description link published_parsed")

FeedDownloader = Callable[[str], Iterable[FeedEntry]]
FailureNotifier = Callable[[int], None]
