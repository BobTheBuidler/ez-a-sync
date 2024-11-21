"""
This module provides asynchronous task management utilities, specifically focused on creating and handling mappings of tasks.

The main components include:
- TaskMapping: A class for managing and asynchronously generating tasks based on input iterables.
- TaskMappingKeys: A view to asynchronously iterate over the keys of a TaskMapping.
- TaskMappingValues: A view to asynchronously iterate over the values of a TaskMapping.
- TaskMappingItems: A view to asynchronously iterate over the items (key-value pairs) of a TaskMapping.
"""
from a_sync._typing import *
import asyncio
from _typeshed import Incomplete
from a_sync.a_sync.base import ASyncGenericBase
from a_sync.asyncio.gather import Excluder
from a_sync.iter import ASyncIterator
from collections.abc import Generator
from typing import Any

__all__ = ["TaskMapping", "TaskMappingKeys", "TaskMappingValues", "TaskMappingItems"]

class TaskMapping(DefaultDict[K, "asyncio.Task[V]"], AsyncIterable[Tuple[K, V]]):
    """
    A mapping of keys to asynchronous tasks with additional functionality.

    `TaskMapping` is a specialized dictionary that maps keys to `asyncio` Tasks. It provides
    convenient methods for creating, managing, and iterating over these tasks asynchronously.

    Tasks are created automatically for each key using a provided function. You cannot manually set items in a `TaskMapping` using dictionary-like syntax.

    Example:
        >>> async def fetch_data(url: str) -> str:
        ...     async with aiohttp.ClientSession() as session:
        ...         async with session.get(url) as response:
        ...             return await response.text()
        ...
        >>> tasks = TaskMapping(fetch_data, [\'http://example.com\', \'https://www.python.org\'], name=\'url_fetcher\', concurrency=5)
        >>> async for key, result in tasks:
        ...     print(f"Data for {key}: {result}")
        ...
        Data for python.org: http://python.org
        Data for example.com: http://example.com

    Note:
        You cannot manually set items in a `TaskMapping` using dictionary-like syntax. Tasks are created and managed internally.

    See Also:
        - :class:`asyncio.Task`
        - :func:`asyncio.create_task`
        - :func:`a_sync.asyncio.create_task`
    """

    concurrency: Optional[int]
    __iterables__: Tuple[AnyIterableOrAwaitableIterable[K], ...]
    __wrapped__: Incomplete
    def __init__(
        self,
        wrapped_func: MappingFn[K, P, V] = None,
        *iterables: AnyIterableOrAwaitableIterable[K],
        name: str = "",
        concurrency: Optional[int] = None,
        **wrapped_func_kwargs: P.kwargs
    ) -> None:
        """
        Initialize a TaskMapping instance.

        Args:
            wrapped_func: A callable that takes a key and additional parameters and returns an Awaitable.
            *iterables: Any number of iterables whose elements will be used as keys for task generation.
            name: An optional name for the tasks created by this mapping.
            concurrency: Maximum number of tasks to run concurrently.
            **wrapped_func_kwargs: Additional keyword arguments to be passed to wrapped_func.

        Example:
            async def process_item(item: int) -> int:
                await asyncio.sleep(1)
                return item * 2

            task_map = TaskMapping(process_item, [1, 2, 3], concurrency=2)
        """

    def __hash__(self) -> int: ...
    def __setitem__(self, item: Any, value: Any) -> None: ...
    def __getitem__(self, item: K) -> asyncio.Task[V]: ...
    def __await__(self) -> Generator[Any, None, Dict[K, V]]:
        """Wait for all tasks to complete and return a dictionary of the results."""

    async def __aiter__(self, pop: bool = False) -> AsyncIterator[Tuple[K, V]]:
        """Asynchronously iterate through all key-task pairs, yielding the key-result pair as each task completes."""

    def __delitem__(self, item: K) -> None: ...
    def keys(self, pop: bool = False) -> TaskMappingKeys[K, V]: ...
    def values(self, pop: bool = False) -> TaskMappingValues[K, V]: ...
    def items(self, pop: bool = False) -> TaskMappingValues[K, V]: ...
    async def close(self) -> None: ...
    async def map(
        self,
        *iterables: AnyIterableOrAwaitableIterable[K],
        pop: bool = True,
        yields: Literal["keys", "both"] = "both"
    ) -> AsyncIterator[Tuple[K, V]]:
        """
        Asynchronously map iterables to tasks and yield their results.

        Args:
            *iterables: Iterables to map over.
            pop: Whether to remove tasks from the internal storage once they are completed.
            yields: Whether to yield \'keys\', \'values\', or \'both\' (key-value pairs).

        Yields:
            Depending on `yields`, either keys, values,
            or tuples of key-value pairs representing the results of completed tasks.

        Example:
            async def process_item(item: int) -> int:
                await asyncio.sleep(1)
                return item * 2

            task_map = TaskMapping(process_item)
            async for key, result in task_map.map([1, 2, 3]):
                print(f"Processed {key}: {result}")
        """

    async def all(self, pop: bool = True) -> bool: ...
    async def any(self, pop: bool = True) -> bool: ...
    async def max(self, pop: bool = True) -> V: ...
    async def min(self, pop: bool = True) -> V:
        """Return the minimum result from the tasks in the mapping."""

    async def sum(self, pop: bool = False) -> V:
        """Return the sum of the results from the tasks in the mapping."""

    async def yield_completed(self, pop: bool = True) -> AsyncIterator[Tuple[K, V]]:
        """
        Asynchronously yield tuples of key-value pairs representing the results of any completed tasks.

        Args:
            pop: Whether to remove tasks from the internal storage once they are completed.

        Yields:
            Tuples of key-value pairs representing the results of completed tasks.

        Example:
            async def process_item(item: int) -> int:
                await asyncio.sleep(1)
                return item * 2

            task_map = TaskMapping(process_item, [1, 2, 3])
            async for key, result in task_map.yield_completed():
                print(f"Completed {key}: {result}")
        """

    async def gather(
        self,
        return_exceptions: bool = False,
        exclude_if: Excluder[V] = None,
        tqdm: bool = False,
        **tqdm_kwargs: Any
    ) -> Dict[K, V]:
        """Wait for all tasks to complete and return a dictionary of the results."""

    def clear(self, cancel: bool = False) -> None:
        """# TODO write docs for this"""

class _NoRunningLoop(Exception): ...
class _EmptySequenceError(ValueError): ...

class _TaskMappingView(ASyncGenericBase, Iterable[T], Generic[T, K, V]):
    """
    Base class for TaskMapping views that provides common functionality.
    """

    __view__: Incomplete
    __mapping__: Incomplete
    def __init__(
        self, view: Iterable[T], task_mapping: TaskMapping[K, V], pop: bool = False
    ) -> None: ...
    def __iter__(self) -> Iterator[T]: ...
    def __await__(self) -> Generator[Any, None, List[T]]: ...
    def __len__(self) -> int: ...
    async def aiterbykeys(self, reverse: bool = False) -> ASyncIterator[T]: ...
    async def aiterbyvalues(self, reverse: bool = False) -> ASyncIterator[T]: ...

class TaskMappingKeys(_TaskMappingView[K, K, V], Generic[K, V]):
    """
    Asynchronous view to iterate over the keys of a TaskMapping.
    """

    async def __aiter__(self) -> AsyncIterator[K]: ...

class TaskMappingItems(_TaskMappingView[Tuple[K, V], K, V], Generic[K, V]):
    """
    Asynchronous view to iterate over the items (key-value pairs) of a TaskMapping.
    """

    async def __aiter__(self) -> AsyncIterator[Tuple[K, V]]: ...

class TaskMappingValues(_TaskMappingView[V, K, V], Generic[K, V]):
    """
    Asynchronous view to iterate over the values of a TaskMapping.
    """

    async def __aiter__(self) -> AsyncIterator[V]: ...
