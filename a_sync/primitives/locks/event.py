
import asyncio
from a_sync.primitives._loggable import _Loggable

class Event(asyncio.Event, _Loggable):
    """asyncio.Event but with some additional debug logging to help detect deadlocks."""
    def __init__(self):
        self._task = None
        self._counter = 0
        super().__init__()
    
    async def wait(self) -> bool:
        if self.is_set():
            return True
        if self._task is None:
            self._task = asyncio.create_task(self._debug_helper())
        return await super().wait()
        
    async def _debug_helper(self) -> None:
        while not self.is_set():
            self.logger.debug(f"Waiting for {self}")
            await asyncio.sleep(5)
        self._task = None
