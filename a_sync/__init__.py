"""
This module initializes the a_sync library by importing and organizing various components, utilities, and classes.
It provides a convenient and unified interface for asynchronous programming with a focus on flexibility and efficiency.

The `a_sync` library offers decorators and base classes to facilitate writing both synchronous and asynchronous code.
It includes the `@a_sync()` decorator and the `ASyncGenericBase` class, which allow for creating functions and classes
that can operate in both synchronous and asynchronous contexts. Additionally, it provides enhanced asyncio primitives,
such as queues and locks, with extra functionality.

Modules and components included:
    - :mod:`~a_sync.aliases`, :mod:`~a_sync.exceptions`, :mod:`~a_sync.iter`, :mod:`~a_sync.task`: Core modules of the library.
    - :class:`~ASyncGenericBase`, :class:`~ASyncGenericSingleton`, :func:`~a_sync`: Base classes and decorators for dual-context execution.
    - :class:`~ASyncCachedPropertyDescriptor`, :class:`~ASyncPropertyDescriptor`, `cached_property`, `property`: Property descriptors for async properties.
    - :func:`~as_completed`, :func:`~create_task`, :func:`~gather`: Enhanced asyncio functions.
    - Executors: :class:`~AsyncThreadPoolExecutor`, :class:`~AsyncProcessPoolExecutor`, :class:`~PruningThreadPoolExecutor` for async execution.
    - Iterators: :class:`~ASyncIterable`, :class:`~ASyncIterator`, :class:`~filter`, :class:`~sorted` for async iteration.
    - Utilities: :func:`~all`, :func:`~any`, :func:`~as_yielded` for async utilities.
    - :func:`~a_sync.a_sync.modifiers.semaphores.apply_semaphore`: Function to apply semaphores to coroutines.
    - :class:`~TaskMapping`: A class for managing and asynchronously generating tasks based on input iterables.

Alias for backward compatibility:
- :class:`~ASyncBase` is an alias for :class:`~ASyncGenericBase`, which will be removed eventually, probably in version 0.1.0.

Examples:
    Using the `@a_sync` decorator:
    >>> from a_sync import a_sync
    >>> @a_sync
    ... async def my_function():
    ...     return "Hello, World!"
    >>> result = await my_function()
    >>> print(result)

    Using `ASyncGenericBase` for dual-context classes:
    >>> from a_sync import ASyncGenericBase
    >>> class MyClass(ASyncGenericBase):
    ...     async def my_method(self):
    ...         return "Hello from MyClass"
    >>> obj = MyClass()
    >>> result = await obj.my_method()
    >>> print(result)

    Using `TaskMapping` for asynchronous task management:
    >>> from a_sync import TaskMapping
    >>> async def fetch_data(url):
    ...     return f"Data from {url}"
    >>> tasks = TaskMapping(fetch_data, ['http://example.com', 'https://www.python.org'])
    >>> async for key, result in tasks:
    ...     print(f"Data for {key}: {result}")

See Also:
    - :mod:`a_sync.a_sync`: Contains the core classes and decorators.
    - :mod:`a_sync.asyncio`: Provides enhanced asyncio functions.
    - :mod:`a_sync.primitives`: Includes modified versions of standard asyncio primitives.
"""

from a_sync import aliases, exceptions, functools, iter, task
from a_sync.a_sync import ASyncGenericBase, ASyncGenericSingleton, a_sync
from a_sync.a_sync.modifiers.semaphores import apply_semaphore
from a_sync.a_sync.property import ASyncCachedPropertyDescriptor, ASyncPropertyDescriptor
from a_sync.a_sync.property import ASyncCachedPropertyDescriptor as cached_property
from a_sync.a_sync.property import ASyncPropertyDescriptor as property
from a_sync.asyncio import as_completed, create_task, gather, cgather, igather
from a_sync.executor import *
from a_sync.executor import AsyncThreadPoolExecutor as ThreadPoolExecutor
from a_sync.executor import AsyncProcessPoolExecutor as ProcessPoolExecutor
from a_sync.future import ASyncFuture, future  # type: ignore [attr-defined]
from a_sync.iter import ASyncFilter as filter
from a_sync.iter import ASyncSorter as sorted
from a_sync.iter import ASyncIterable, ASyncIterator
from a_sync.primitives import *
from a_sync.task import TaskMapping as map
from a_sync.task import TaskMapping
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
    "cgather",
    "igather",
    "as_completed",
    # functions
    "a_sync",
    "all",
    "any",
    "as_yielded",
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


def _patch_async_property() -> None:
    import async_property.base as base
    import async_property.cached as cached
    from a_sync.async_property.proxy import AwaitableOnly, AwaitableProxy

    base.AwaitableOnly = AwaitableOnly
    cached.AwaitableOnly = AwaitableOnly
    cached.AwaitableProxy = AwaitableProxy


_patch_async_property()
