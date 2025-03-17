from asyncio import AbstractEventLoop, Future, Task
from typing import TYPE_CHECKING, Any, Generic, Optional, Tuple, TypeVar
from weakref import WeakSet

if TYPE_CHECKING:
    from a_sync.primitives.queue import SmartProcessingQueue

_T = TypeVar("_T")

_Args = Tuple[Any]
_Kwargs = Tuple[Tuple[str, Any]]
_Key = Tuple[_Args, _Kwargs]

class _SmartFutureMixin(Generic[_T]):
    """
    Mixin class that provides common functionality for smart futures and tasks.

    This mixin provides methods for managing waiters and integrating with a smart processing queue.
    It uses weak references to manage resources efficiently.

    Example:
        Creating a SmartFuture and awaiting it:

        ```python
        future = SmartFuture()
        result = await future
        ```

        Creating a SmartTask and awaiting it:

        ```python
        task = SmartTask(coro=my_coroutine())
        result = await task
        ```

    See Also:
        - :class:`SmartFuture`
        - :class:`SmartTask`
    """

    _queue: Optional["SmartProcessingQueue[Any, Any, _T]"] = None
    _key: _Key
    _waiters: "WeakSet[SmartTask[_T]]"

class SmartFuture(_SmartFutureMixin[_T], Future):
    """
    A smart future that tracks waiters and integrates with a smart processing queue.

    Inherits from both :class:`_SmartFutureMixin` and :class:`asyncio.Future`, providing additional functionality
    for tracking waiters and integrating with a smart processing queue.

    Example:
        Creating and awaiting a SmartFuture:

        ```python
        future = SmartFuture()
        await future
        ```

    See Also:
        - :class:`_SmartFutureMixin`
        - :class:`asyncio.Future`
    """

def create_future(
    *,
    queue: Optional["SmartProcessingQueue"] = None,
    key: Optional[_Key] = None,
    loop: Optional[AbstractEventLoop] = None,
) -> SmartFuture[_T]:
    """
    Create a :class:`~SmartFuture` instance.

    Args:
        queue: Optional; a smart processing queue.
        key: Optional; a key identifying the future.
        loop: Optional; the event loop.

    Returns:
        A SmartFuture instance.

    Example:
        Creating a SmartFuture using the factory function:

        ```python
        future = create_future(queue=my_queue, key=my_key)
        ```

    See Also:
        - :class:`SmartFuture`
    """

class SmartTask(_SmartFutureMixin[_T], Task):
    """
    A smart task that tracks waiters and integrates with a smart processing queue.

    Inherits from both :class:`_SmartFutureMixin` and :class:`asyncio.Task`, providing additional functionality
    for tracking waiters and integrating with a smart processing queue.

    Example:
        Creating and awaiting a SmartTask:

        ```python
        task = SmartTask(coro=my_coroutine())
        await task
        ```

    See Also:
        - :class:`_SmartFutureMixin`
        - :class:`asyncio.Task`
    """
