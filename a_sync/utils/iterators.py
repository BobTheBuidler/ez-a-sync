
import asyncio
import asyncio.futures
import logging
import traceback
from types import TracebackType

from a_sync._typing import *
from a_sync.primitives.queue import Queue

logger = logging.getLogger(__name__)


async def exhaust_iterator(iterator: AsyncIterator[T], *, queue: Optional[asyncio.Queue] = None) -> None:
    """
    Asynchronously iterates over items from the given async iterator and optionally places them into a queue.

    This function is a utility to exhaust an async iterator, with an option to forward the iterated items to a provided asyncio.Queue. It's particularly useful when dealing with asynchronous operations that produce items to be consumed by other parts of an application, enabling a producer-consumer pattern.

    Args:
        iterator (AsyncIterator[T]): The async iterator to exhaust.
        queue (Optional[asyncio.Queue]): An optional queue where iterated items will be placed. If None, items are simply consumed.

    Returns:
        None
    """
    async for thing in iterator:
        if queue:
            logger.debug('putting %s from %s to queue %s', thing, iterator, queue)
            queue.put_nowait(thing)


async def exhaust_iterators(iterators, *, queue: Optional[asyncio.Queue] = None, join: bool = False) -> None:
    """    
    Asynchronously iterates over multiple async iterators concurrently and optionally places their items into a queue.

    This function leverages asyncio.gather to concurrently exhaust multiple async iterators. It's useful in scenarios where items from multiple async sources need to be processed or collected together, supporting concurrent operations and efficient multitasking.

    Args:
        iterators: A sequence of async iterators to be exhausted concurrently.
        queue (Optional[asyncio.Queue]): An optional queue where items from all iterators will be placed. If None, items are simply consumed.
        join (Optional[bool]): If a queue was provided and join is True, this coroutine will continue to run until all queue items have been processed.

    Returns:
        None
    """
    for x in await asyncio.gather(*[exhaust_iterator(iterator, queue=queue) for iterator in iterators], return_exceptions=True):
        if isinstance(x, Exception):
            # raise it with its original traceback instead of from here
            raise x.with_traceback(x.__traceback__)
    if queue:
        queue.put_nowait(_Done())
        if join:
            await queue.join()
    elif join:
        raise ValueError("You must provide a `queue` to use kwarg `join`")

    
T0 = TypeVar('T0')
T1 = TypeVar('T1')
T2 = TypeVar('T2')
T3 = TypeVar('T3')
T4 = TypeVar('T4')
T5 = TypeVar('T5')
T6 = TypeVar('T6')
T7 = TypeVar('T7')
T8 = TypeVar('T8')
T9 = TypeVar('T9')

@overload
def as_yielded(*iterators: AsyncIterator[T]) -> AsyncIterator[T]:...
@overload
def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3], iterator4: AsyncIterator[T4], iterator5: AsyncIterator[T5], iterator6: AsyncIterator[T6], iterator7: AsyncIterator[T7], iterator8: AsyncIterator[T8], iterator9: AsyncIterator[T9]) -> AsyncIterator[Union[T0, T1, T2, T3, T4, T5, T6, T7, T8, T9]]:...
@overload
def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3], iterator4: AsyncIterator[T4], iterator5: AsyncIterator[T5], iterator6: AsyncIterator[T6], iterator7: AsyncIterator[T7], iterator8: AsyncIterator[T8]) -> AsyncIterator[Union[T0, T1, T2, T3, T4, T5, T6, T7, T8]]:...
@overload
def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3], iterator4: AsyncIterator[T4], iterator5: AsyncIterator[T5], iterator6: AsyncIterator[T6], iterator7: AsyncIterator[T7]) -> AsyncIterator[Union[T0, T1, T2, T3, T4, T5, T6, T7]]:...
@overload
def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3], iterator4: AsyncIterator[T4], iterator5: AsyncIterator[T5], iterator6: AsyncIterator[T6]) -> AsyncIterator[Union[T0, T1, T2, T3, T4, T5, T6]]:...
@overload
def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3], iterator4: AsyncIterator[T4], iterator5: AsyncIterator[T5]) -> AsyncIterator[Union[T0, T1, T2, T3, T4, T5]]:...
@overload
def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3], iterator4: AsyncIterator[T4]) -> AsyncIterator[Union[T0, T1, T2, T3, T4]]:...
@overload
def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3]) -> AsyncIterator[Union[T0, T1, T2, T3]]:...
@overload
def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2]) -> AsyncIterator[Union[T0, T1, T2]]:...
@overload
def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1]) -> AsyncIterator[Union[T0, T1]]:...
@overload
def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], *iterators: AsyncIterator[T]) -> AsyncIterator[Union[T0, T1, T2, T]]:...
async def as_yielded(*iterators: AsyncIterator[T]) -> AsyncIterator[T]:  # type: ignore [misc]
    """
    Merges multiple async iterators into a single async iterator that yields items as they become available from any of the source iterators.

    This function is designed to streamline the handling of multiple asynchronous data streams by consolidating them into a single asynchronous iteration context. It enables concurrent fetching and processing of items from multiple sources, improving efficiency and simplifying code structure when dealing with asynchronous operations.

    The merging process is facilitated by internally managing a queue where items from the source iterators are placed as they are fetched. This mechanism ensures that the merged stream of items is delivered in an order determined by the availability of items from the source iterators, rather than their original sequence.

    Args:
        *iterators: Variable length list of AsyncIterator objects to be merged.

    Returns:
        AsyncIterator[T]: An async iterator that yields items from the input async iterators as they become available.

    Note:
        This implementation leverages asyncio tasks and queues to efficiently manage the asynchronous iteration and merging process. It handles edge cases such as early termination and exception management, ensuring robustness and reliability.
    """
    # hypothesis idea: _Done should never be exposed to user, works for all desired input types
    queue: Queue[Union[T, _Done]] = Queue()
    
    def _as_yielded_done_callback(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        if e := t.exception(): 
            traceback.extract_stack
            traceback.clear_frames(e.__traceback__)
            queue.put_nowait(_Done(e))

    task = asyncio.create_task(
        coro=exhaust_iterators(iterators, queue=queue, join=True), 
        name=f"a_sync.as_yielded queue populating task for {iterators}",
    )
    
    task.add_done_callback(_as_yielded_done_callback)

    while not task.done():
        try:
            items = await queue.get_all()
        except asyncio.CancelledError:
            # cleanup lingering objects and reraise
            del task
            del queue
            raise
        for item in items:
            queue.task_done()
            if isinstance(item, _Done):
                assert queue.empty()
                del task
                del queue
                if item._exc:
                    raise type(item._exc)(*item._exc.args).with_traceback(item._tb) from item._exc.__cause__
                return
            yield item

    # ensure it isn't done due to an internal exception
    await task

        
class _Done:
    """
    A sentinel class used to signal the completion of processing in the as_yielded function.

    This class acts as a marker to indicate that all items have been processed and the asynchronous iteration can be concluded. It is used internally within the implementation of as_yielded to efficiently manage the termination of the iteration process once all source iterators have been exhausted.
    """
    def __init__(self, exc: Optional[Exception] = None) -> None:
        self._exc = exc
    @property
    def _tb(self) -> TracebackType:
        return self._exc.__traceback__  # type: ignore [union-attr]

__all__ = ["as_yielded", "exhaust_iterator", "exhaust_iterators"]
