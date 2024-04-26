
from a_sync import aliases, exceptions
from a_sync.base import ASyncGenericBase
from a_sync.decorator import a_sync
from a_sync.future import ASyncFuture, future  # type: ignore [attr-defined]
from a_sync.iter import ASyncIterable, ASyncIterator
from a_sync.modifiers.semaphores import apply_semaphore
from a_sync.primitives import *
from a_sync.property import ASyncCachedPropertyDescriptor, ASyncPropertyDescriptor, cached_property, property
from a_sync.singleton import ASyncGenericSingleton
from a_sync.task import TaskMapping as map
from a_sync.task import TaskMapping, create_task
from a_sync.utils import all, any, as_completed, as_yielded, gather

# I alias the aliases for your convenience.
# I prefer "aka" but its meaning is not intuitive when reading code so I created both aliases for you to choose from.
# NOTE: Overkill? Maybe.
aka = alias = aliases

# alias for backward-compatability, will be removed eventually, probably in 0.1.0
ASyncBase = ASyncGenericBase

__all__ = [
    # modules
    "exceptions",
    # functions
    "all",
    "any",
    "as_completed",
    "as_yielded",
    "create_task",
    "exhaust_iterator",
    "exhaust_iterators",
    "gather", 
    "map",
    # classes
    "ASyncIterable",
    "ASyncIterator",
    "ASyncGenericSingleton",
    "TaskMapping", 
    # property
    "cached_property",
    "property",
    "ASyncPropertyDescriptor",
    "ASyncCachedPropertyDescriptor",
    # semaphores
    "Semaphore",
    "PrioritySemaphore",
    "ThreadsafeSemaphore",
    # queues
    "Queue",
    "ProcessingQueue",
    "SmartProcessingQueue",
    # locks
    "CounterLock",
    "Event",
    # executors
    "AsyncThreadPoolExecutor",
    "ThreadPoolExecutor",
    "PruningThreadPoolExecutor",
    "AsyncProcessPoolExecutor",
    "ProcessPoolExecutor",
]
