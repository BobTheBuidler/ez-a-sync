
from a_sync import aliases
from a_sync.base import ASyncGenericBase
from a_sync.decorator import a_sync
from a_sync.future import ASyncFuture, future
from a_sync.iter import ASyncIterable, ASyncIterator
from a_sync.modifiers.semaphores import apply_semaphore
from a_sync.primitives import *
from a_sync.singleton import ASyncGenericSingleton
from a_sync.utils import all, any, as_yielded
from a_sync.utils.as_completed import as_completed
from a_sync.utils.gather import gather

# I alias the aliases for your convenience.
# I prefer "aka" but its meaning is not intuitive when reading code so I created both aliases for you to choose from.
# NOTE: Overkill? Maybe.
aka = alias = aliases

# alias for backward-compatability, will be removed eventually, probably in 0.1.0
ASyncBase = ASyncGenericBase


__all__ = [
    "all",
    "any",
    "as_completed",
    "as_yielded",
    "exhaust_iterator",
    "exhaust_iterators",
    "gather", 
    "ASyncIterable",
    "ASyncIterator",
]