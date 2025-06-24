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
    Wait for an awaitable, shielding it from cancellation.

    This function awaits the given awaitable, similarly to using the `await`
    operator directly. The key difference is that if the coroutine awaiting the
    result is cancelled, the underlying task running the awaitable is not cancelled.
    Instead, cancellation propagates only to the awaiting coroutine while the awaited
    operation continues to run.

    Note:
      If the awaited coroutine is cancelled by external means, its cancellation will
      still affect the shield operation.

    Example:
      Basic usage:
      ::
          result = await shield(my_coroutine())

      Ignoring cancellation (not recommended):
      ::
          try:
              result = await shield(my_coroutine())
          except CancelledError:
              result = None

    Args:
      arg: The awaitable to shield from cancellation.

    Returns:
      A :class:`SmartFuture` or :class:`asyncio.Future` instance.

    See Also:
      - :func:`asyncio.shield`
    """

class _SmartFutureMixin(Generic[_T]):
    """
    Mixin class that provides common functionality for smart futures and tasks.

    This mixin provides methods for managing waiters and integrating with a smart
    processing queue. It uses weak references to manage resources efficiently.

    Example:
      Creating and awaiting a smart future:

      ::
          future = SmartFuture()
          result = await future

      Creating and awaiting a smart task:

      ::
          task = SmartTask(coro=my_coroutine())
          result = await task

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

      ::
          future = SmartFuture()
          await future

    See Also:
      - :class:`_SmartFutureMixin`
      - :class:`asyncio.Future`
    """

    def __await__(self) -> Generator[Any, None, _T]:
        """
        Await the SmartFuture, handling waiters and logging.

        Yields:
          The result of the future.

        Example:
          ::
              future = SmartFuture()
              result = await future
        """
        
def create_future(
    *,
    queue: Optional["SmartProcessingQueue"] = None,
    key: Optional[_Key] = None,
    loop: Optional[AbstractEventLoop] = None,
) -> SmartFuture[_T]:
    """
    Create a :class:`SmartFuture` instance.

    Args:
      queue: Optional; a smart processing queue.
      key: Optional; a key identifying the future.
      loop: Optional; the event loop.

    Returns:
      A SmartFuture instance.

    Example:
      Creating a SmartFuture using the factory function:

      ::
          future = create_future(queue=my_queue, key=my_key)

    See Also:
      - :class:`SmartFuture`
    """
    return _SmartFuture(queue=queue, key=key, loop=loop or get_event_loop())

class SmartTask(_SmartFutureMixin[_T], Task):
    """
    A smart task that tracks waiters and integrates with a smart processing queue.

    Inherits from both :class:`_SmartFutureMixin` and :class:`asyncio.Task`, providing additional functionality
    for tracking waiters and integrating with a smart processing queue.

    Example:
      Creating and awaiting a SmartTask:

      ::
          task = SmartTask(coro=my_coroutine())
          result = await task

    See Also:
      - :class:`_SmartFutureMixin`
      - :class:`asyncio.Task`
    """

    def __await__(self) -> Generator[Any, None, _T]:
        """
        Await the SmartTask, handling waiters and logging.

        Yields:
          The result of the task.

        Example:
          ::
              task = SmartTask(coro=my_coroutine())
              result = await task
        """
        
def set_smart_task_factory(loop: AbstractEventLoop = None) -> None:
    """
    Set the event loop's task factory to :func:`smart_task_factory` so all tasks will be SmartTask instances.

    Args:
      loop: Optional; the event loop. If None, the current event loop is used.

    Example:
      Setting the smart task factory for the current event loop:

      ::
          set_smart_task_factory()

    See Also:
      - :func:`smart_task_factory`
    """
    
cpdef object smart_task_factory(loop: AbstractEventLoop, coro: Awaitable[_T]):
    """
    Task factory function that an event loop calls to create new tasks.

    This factory function utilizes ez-a-sync's custom :class:`SmartTask` implementation.

    Args:
      loop: The event loop.
      coro: The coroutine to run in the task.

    Returns:
      A SmartTask instance running the provided coroutine.

    Example:
      Using the smart task factory to create a SmartTask:

      ::
          loop = asyncio.get_event_loop()
          task = smart_task_factory(loop, my_coroutine())

    See Also:
      - :func:`set_smart_task_factory`
      - :class:`SmartTask`
    """
    return _SmartTask(coro, loop=loop)

cpdef object shield(arg: Awaitable[_T]) -> Union[SmartFuture[_T], "Future[_T]"]:
    """
    Wait for an awaitable, shielding it from cancellation.

    This function awaits the given awaitable, similar to using the `await`
    operator directly. However, if the coroutine awaiting the result is cancelled,
    the underlying task is not cancelled. Cancellation propagates only to the awaiting
    coroutine while the awaited operation continues to run.

    Note:
      If the awaited coroutine is cancelled by external factors, its cancellation will
      still propagate to the shielded operation.

    Example:
      Basic usage:
      ::
          result = await shield(my_coroutine())

      Ignoring cancellation (not recommended):
      ::
          try:
              result = await shield(my_coroutine())
          except CancelledError:
              result = None

    Args:
      arg: The awaitable to shield from cancellation.

    Returns:
      A :class:`SmartFuture` or :class:`asyncio.Future` instance.

    See Also:
      - :func:`asyncio.shield`
    """
    inner = ensure_future(arg)
    if _is_done(inner):
        # Shortcut.
        return inner

    loop = _get_loop(inner)
    outer = _SmartFuture(loop=loop)

    # special handling to connect SmartFutures to SmartTasks if enabled
    if (waiters := getattr(inner, "_waiters", None)) is not None:
        waiters.add(outer)

    _inner_done_callback, _outer_done_callback = _get_done_callbacks(inner, outer)

    inner.add_done_callback(_inner_done_callback)
    outer.add_done_callback(_outer_done_callback)
    return outer