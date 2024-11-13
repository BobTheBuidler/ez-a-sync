"""
This module initializes the a_sync library by importing and organizing various components, utilities, and classes.
It provides a convenient and unified interface for asynchronous programming with a focus on flexibility and efficiency.

The `a_sync` library offers decorators and base classes to facilitate writing both synchronous and asynchronous code.
It includes the `@a_sync()` decorator and the `ASyncGenericBase` class, which allow for creating functions and classes
that can operate in both synchronous and asynchronous contexts. Additionally, it provides enhanced asyncio primitives,
such as queues and locks, with extra functionality.

Modules and components included:
- `aliases`, `exceptions`, `iter`, `task`: Core modules of the library.
- `ASyncGenericBase`, `ASyncGenericSingleton`, `a_sync`: Base classes and decorators for dual-context execution.
- `apply_semaphore`: Function to apply semaphores to coroutines.
- `ASyncCachedPropertyDescriptor`, `ASyncPropertyDescriptor`, `cached_property`, `property`: Property descriptors for async properties.
- `as_completed`, `create_task`, `gather`: Enhanced asyncio functions.
- Executors: `AsyncThreadPoolExecutor`, `AsyncProcessPoolExecutor`, `PruningThreadPoolExecutor` for async execution.
- Iterators: `ASyncFilter`, `ASyncSorter`, `ASyncIterable`, `ASyncIterator` for async iteration.
- Utilities: `all`, `any`, `as_yielded` for async utilities.

Alias for backward compatibility:
- `ASyncBase` is an alias for `ASyncGenericBase`, which will be removed eventually, probably in version 0.1.0.
"""

from a_sync import aliases, exceptions, iter, task
from a_sync.a_sync import ASyncGenericBase, ASyncGenericSingleton, a_sync
from a_sync.a_sync.modifiers.semaphores import apply_semaphore
from a_sync.a_sync.property import (
    ASyncCachedPropertyDescriptor,
    ASyncPropertyDescriptor,
    cached_property,
    property,
)
from a_sync.asyncio import as_completed, create_task, gather
from a_sync.executor import *
from a_sync.executor import AsyncThreadPoolExecutor as ThreadPoolExecutor
from a_sync.executor import AsyncProcessPoolExecutor as ProcessPoolExecutor
from a_sync.future import ASyncFuture, future  # type: ignore [attr-defined]
from a_sync.iter import ASyncFilter as filter
from a_sync.iter import ASyncSorter as sorted
from a_sync.iter import ASyncIterable, ASyncIterator
from a_sync.primitives import *
from a_sync.task import TaskMapping as map
from a_sync.task import TaskMapping, create_task
from a_sync.utils import all, any, as_yielded

# I alias the aliases for your convenience.
# I prefer "aka" but its meaning is not intuitive when reading code so I created both aliases for you to choose from.
# NOTE: Overkill? Maybe.
aka = alias = aliases

# alias for backward-compatability, will be removed eventually, probably in 0.1.0
ASyncBase = ASyncGenericBase

__all__ = [
    # modules
    "exceptions",
    "iter",
    "task",
    # builtins
    "sorted",
    "filter",
    # asyncio
    "create_task",
    "gather",
    "as_completed",
    # functions
    "a_sync",
    "all",
    "any",
    "as_yielded",
    "exhaust_iterator",
    "exhaust_iterators",
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
    "PruningThreadPoolExecutor",
    "AsyncProcessPoolExecutor",
    # executor aliases
    "ThreadPoolExecutor",
    "ProcessPoolExecutor",
]
