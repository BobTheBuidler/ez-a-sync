from asyncio import AbstractEventLoop, Future, Task
from typing import TYPE_CHECKING, Any, Awaitable, Generic, Optional, Tuple, TypeVar, Union
from weakref import WeakSet

if TYPE_CHECKING:
    from a_sync.primitives.queue import SmartProcessingQueue

_T = TypeVar("_T")

_Args = Tuple[Any]
_Kwargs = Tuple[Tuple[str, Any]]
_Key = Tuple[_Args, _Kwargs]

def shield(arg: Awaitable[_T]) -> Union[SmartFuture[_T], "Future[_T]"]:
    """
    Wait for a future, shielding it from cancellation.

    The statement

        res = await shield(something())

    is exactly equivalent to the statement

        res = await something()

    *except* that if the coroutine containing it is cancelled, the
    task running in something() is not cancelled.  From the POV of
    something(), the cancellation did not happen.  But its caller is
    still cancelled, so the yield-from expression still raises
    CancelledError.  Note: If something() is cancelled by other means
    this will still cancel shield().

    If you want to completely ignore cancellation (not recommended)
    you can combine shield() with a try/except clause, as follows:

        try:
            res = await shield(something())
        except CancelledError:
            res = None

    Args:
        arg: The awaitable to shield from cancellation.
        loop: Optional; the event loop. Deprecated since Python 3.8.

    Returns:
        A :class:`SmartFuture` or :class:`asyncio.Future` instance.

    Example:
        Using shield to protect a coroutine from cancellation:

        ```python
        result = await shield(my_coroutine())
        ```

    See Also:
        - :func:`asyncio.shield`
    """

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

def set_smart_task_factory(loop: AbstractEventLoop = None) -> None:
    """
    Set the event loop's task factory to :func:`~smart_task_factory` so all tasks will be SmartTask instances.

    Args:
        loop: Optional; the event loop. If None, the current event loop is used.

    Example:
        Setting the smart task factory for the current event loop:

        ```python
        set_smart_task_factory()
        ```

    See Also:
        - :func:`smart_task_factory`
    """
