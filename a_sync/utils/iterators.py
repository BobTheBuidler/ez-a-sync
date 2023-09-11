
import asyncio
from typing import AsyncIterator, Optional, TypeVar, Union, overload
from a_sync.primitives.queue import Queue

T = TypeVar('T')

async def exhaust_iterator(iterator: AsyncIterator[T], *, queue: Optional[asyncio.Queue] = None) -> None:
    if queue:
        async for thing in iterator:
            queue.put_nowait(thing)
    else:
        async for thing in iterator:
            pass
        
async def exhaust_iterators(iterators, *, queue: Optional[asyncio.Queue] = None) -> None:
    await asyncio.gather(*[exhaust_iterator(iterator, queue=queue) for iterator in iterators]) 
    
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
async def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3], iterator4: AsyncIterator[T4], iterator5: AsyncIterator[T5], iterator6: AsyncIterator[T6], iterator7: AsyncIterator[T7], iterator8: AsyncIterator[T8], iterator9: AsyncIterator[T9]) -> AsyncIterator[Union[T0, T1, T2, T3, T4, T5, T6, T7, T8, T9]]:...
@overload
async def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3], iterator4: AsyncIterator[T4], iterator5: AsyncIterator[T5], iterator6: AsyncIterator[T6], iterator7: AsyncIterator[T7], iterator8: AsyncIterator[T8]) -> AsyncIterator[Union[T0, T1, T2, T3, T4, T5, T6, T7, T8]]:...
@overload
async def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3], iterator4: AsyncIterator[T4], iterator5: AsyncIterator[T5], iterator6: AsyncIterator[T6], iterator7: AsyncIterator[T7]) -> AsyncIterator[Union[T0, T1, T2, T3, T4, T5, T6, T7]]:...
@overload
async def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3], iterator4: AsyncIterator[T4], iterator5: AsyncIterator[T5], iterator6: AsyncIterator[T6]) -> AsyncIterator[Union[T0, T1, T2, T3, T4, T5, T6]]:...
@overload
async def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3], iterator4: AsyncIterator[T4], iterator5: AsyncIterator[T5]) -> AsyncIterator[Union[T0, T1, T2, T3, T4, T5]]:...
@overload
async def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3], iterator4: AsyncIterator[T4]) -> AsyncIterator[Union[T0, T1, T2, T3, T4]]:...
@overload
async def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], iterator3: AsyncIterator[T3]) -> AsyncIterator[Union[T0, T1, T2, T3]]:...
@overload
async def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2]) -> AsyncIterator[Union[T0, T1, T2]]:...
@overload
async def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1]) -> AsyncIterator[Union[T0, T1]]:...
@overload
async def as_yielded(iterator0: AsyncIterator[T0], iterator1: AsyncIterator[T1], iterator2: AsyncIterator[T2], *iterators: AsyncIterator[T]) -> AsyncIterator[Union[T0, T1, T2, T]]:...
async def as_yielded(*iterators: AsyncIterator[T]) -> AsyncIterator[T]:
    queue = Queue()
    task = asyncio.create_task(exhaust_iterators(iterators, queue=queue))
    def done_callback(t: asyncio.Task) -> None:
        if t.exception() and not next.done(): 
            next.set_exception(t.exception())
    task.add_done_callback(done_callback)
    while not task.done():
        next = asyncio.ensure_future(queue.get())
        yield await next
        for next in queue.get_nowait(-1):
            yield next
    if e := task.exception():
        raise e

