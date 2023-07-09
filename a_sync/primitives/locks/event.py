
import asyncio
from functools import cached_property

from a_sync.primitives._debug import _DebugDaemonMixin


class Event(asyncio.Event, _DebugDaemonMixin):
    """asyncio.Event but with some additional debug logging to help detect deadlocks."""
    async def wait(self) -> bool:
        if self.is_set():
            return True
        self._ensure_debug_daemon()
        return await super().wait()
    
    @cached_property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop or asyncio.get_event_loop()
        
    async def _debug_daemon(self) -> None:
        while not self.is_set():
            self.logger.debug(f"Waiting for {self}")
            await asyncio.sleep(60)
