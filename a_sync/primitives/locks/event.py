
import asyncio, sys
from functools import cached_property
from typing import Optional

from a_sync.primitives._debug import _DebugDaemonMixin


class Event(asyncio.Event, _DebugDaemonMixin):
    """asyncio.Event but with some additional debug logging to help detect deadlocks."""
    def __init__(self, debug_daemon_interval: int = 300, *, loop: Optional[asyncio.AbstractEventLoop] = None):
        if sys.version_info >= (3, 10):
            super().__init__()
        else:
            super().__init__(loop=loop)
        self._loop = self._loop or asyncio.get_event_loop()
        self._debug_daemon_interval = debug_daemon_interval
    async def wait(self) -> bool:
        if self.is_set():
            return True
        self._ensure_debug_daemon()
        return await super().wait()
    
    @cached_property
    def loop(self) -> asyncio.AbstractEventLoop:
        return 
        
    async def _debug_daemon(self) -> None:
        while not self.is_set():
            await asyncio.sleep(self._debug_daemon_interval)
            if not self.is_set():
                self.logger.debug(f"Waiting for {self}")
