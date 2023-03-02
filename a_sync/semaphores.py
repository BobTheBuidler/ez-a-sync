import asyncio
import functools
from collections import defaultdict
from threading import Thread, current_thread

from a_sync import exceptions
from a_sync._typing import *


class ThreadsafeSemaphore(asyncio.Semaphore):
    """
    While its a bit weird to run multiple event loops, sometimes either you or a lib you're using must do so. 
    When in use in threaded applications, this semaphore will not work as intended but at least your program will function.
    You may need to reduce the semaphore value for multi-threaded applications.
    
    # TL;DR it's a janky fix for an edge case problem and will otherwise function as a normal asyncio.Semaphore.
    """

    def __init__(self, value: Optional[int]) -> None:
        assert isinstance(value, int), f"{value} should be an integer."
        self._value = value
        self.semaphores: DefaultDict[Thread, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(value))  # type: ignore [arg-type]
        self.dummy = DummySemaphore()
    
    @property
    def use_dummy(self) -> bool:
        return self._value is None
    
    @property
    def semaphore(self) -> asyncio.Semaphore:
        if self.use_dummy:
            return self.dummy
        tid = current_thread()
        if tid not in self.semaphores:
            self.semaphores[tid] = asyncio.Semaphore(self._value)
        return self.semaphores[tid]
    
    async def __aenter__(self):
        await self.semaphore.acquire()
    
    async def __aexit__(self, *args):
        self.semaphore.release()


class DummySemaphore(asyncio.Semaphore):
    def __init__(*args, **kwargs):
        ...
    async def __aenter__(self):
        ...
    async def __aexit__(self, *args):
        ...


Semaphore = Union[
    asyncio.Semaphore,
    asyncio.BoundedSemaphore,
    ThreadsafeSemaphore,
    DummySemaphore,
]

@overload
async def apply_semaphore(  # type: ignore [misc]
    coro_fn: Literal[None],
    semaphore: SemaphoreSpec,
) -> AsyncDecorator[P, T]:...

@overload
async def apply_semaphore(
    coro_fn: SemaphoreSpec,
    semaphore: Literal[None],
) -> AsyncDecorator[P, T]:...

@overload
async def apply_semaphore(
    coro_fn: CoroFn[P, T],
    semaphore: SemaphoreSpec,
) -> CoroFn[P, T]:...
    
def apply_semaphore(
    coro_fn: Optional[Union[CoroFn[P, T], SemaphoreSpec]] = None,
    semaphore: SemaphoreSpec = None,
) -> AsyncDecoratorOrCoroFn[P, T]:
    # Parse Inputs
    if isinstance(coro_fn, (int, asyncio.Semaphore)):
        if semaphore is not None:
            raise ValueError("You can only pass in one arg.")
        semaphore = coro_fn
        coro_fn = None
        
    elif not asyncio.iscoroutinefunction(coro_fn):
        raise exceptions.FunctionNotAsync(coro_fn)
        
    # Create the semaphore if necessary
    if isinstance(semaphore, int):
        semaphore = ThreadsafeSemaphore(semaphore)
    elif not isinstance(semaphore, asyncio.Semaphore):
        raise TypeError(f"'semaphore' must either be an integer or a Semaphore object.")
        
    # Create and return the decorator
    def semaphore_decorator(coro_fn: CoroFn[P, T]) -> CoroFn[P, T]:
        @functools.wraps(coro_fn)
        async def semaphore_wrap(*args, **kwargs) -> T:
            async with semaphore:  # type: ignore [union-attr]
                return await coro_fn(*args, **kwargs)
        return semaphore_wrap
    return semaphore_decorator if coro_fn is None else semaphore_decorator(coro_fn)


dummy_semaphore = DummySemaphore()
