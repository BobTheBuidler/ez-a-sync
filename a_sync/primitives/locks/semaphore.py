import asyncio
import functools
import logging
from collections import defaultdict
from threading import Thread, current_thread
from typing import Callable, Literal, Optional, TypeVar

from typing_extensions import ParamSpec

from a_sync.primitives._debug import _DebugDaemonMixin

logger = logging.getLogger(__name__)

T = TypeVar('T')
P = ParamSpec('P')

class Semaphore(asyncio.Semaphore, _DebugDaemonMixin):
    def __init__(self, value: int, name=None, **kwargs) -> None:
        """
        `name` is used only in debug logs to provide useful context
        """
        super().__init__(value, **kwargs)
        self.name = name or self.__origin__ if hasattr(self, '__origin__') else None
        self._decorated = set()
    
    # Dank new functionality
    def __call__(self, fn: Callable[P, T]) -> Callable[P, T]:
        return self.decorate(fn)
    
    def __repr__(self) -> str:
        representation = f"<{self.__class__.__name__} name={self.name} value={self._value} waiters={len(self)}>"
        if self._decorated:
            representation = f"{representation[:-1]} decorates={self._decorated}"
        return representation
    
    def __len__(self) -> int:
        return len(self._waiters) if self._waiters else 0
    
    def decorate(self, fn: Callable[P, T]) -> Callable[P, T]:
        if not asyncio.iscoroutinefunction(fn):
            raise TypeError(f"{fn} must be a coroutine function")
        @functools.wraps(fn)
        async def semaphore_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async with self:
                return await fn(*args, **kwargs)
        self._decorated.add(f"{fn.__module__}.{fn.__name__}")
        return semaphore_wrapper
    
    async def acquire(self) -> bool:
        if self._value <= 0:
            self._ensure_debug_daemon()
        return await super().acquire()
    
    # Everything below just adds some debug logs
    async def _debug_daemon(self) -> None:
        while self._waiters:
            await asyncio.sleep(60)
            self.logger.debug(f"{self} has {len(self)} waiters for any of: {self._decorated}")
  
        
class DummySemaphore(asyncio.Semaphore):
    """It can go where a semaphore goes, but it does nothing."""
    _value = 0
    def __init__(self, name: Optional[str] = None):
        self.name = name
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"
    async def acquire(self) -> Literal[True]:
        return True
    def release(self) -> None:
        ...
    async def __aenter__(self):
        ...
    async def __aexit__(self, *args):
        ...
        

class ThreadsafeSemaphore(Semaphore):
    """
    While its a bit weird to run multiple event loops, sometimes either you or a lib you're using must do so. 
    When in use in threaded applications, this semaphore will not work as intended but at least your program will function.
    You may need to reduce the semaphore value for multi-threaded applications.
    
    # TL;DR it's a janky fix for an edge case problem and will otherwise function as a normal a_sync.Semaphore (which is just an asyncio.Semaphore with extra bells and whistles).
    """

    def __init__(self, value: Optional[int], name: Optional[str] = None) -> None:
        assert isinstance(value, int), f"{value} should be an integer."
        super().__init__(value, name=name)
        self.semaphores: DefaultDict[Thread, Semaphore] = defaultdict(lambda: Semaphore(value, name=self.name))  # type: ignore [arg-type]
        self.dummy = DummySemaphore(name=name)
    
    def __len__(self) -> int:
        return sum(len(sem._waiters) for sem in self.semaphores.values())
    
    @property
    def use_dummy(self) -> bool:
        return self._value is None
    
    @property
    def semaphore(self) -> Semaphore:
        return self.dummy if self.use_dummy else self.semaphores[current_thread()]
    
    async def __aenter__(self):
        await self.semaphore.acquire()
    
    async def __aexit__(self, *args):
        self.semaphore.release()
        