
import abc
import asyncio
from typing import Optional

from a_sync.primitives._loggable import _LoggerMixin


class _DebugDaemonMixin(_LoggerMixin, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def _debug_daemon(self, fut: asyncio.Future, fn, *args, **kwargs) -> None:
        ...    
    def _start_debug_daemon(self, *args, **kwargs) -> "asyncio.Task":
        if self.debug_logs_enabled and asyncio.get_event_loop().is_running():
            return asyncio.create_task(self._debug_daemon(*args, **kwargs))
        # else we return a blank Future since we shouldn't or can't create the daemon
        return asyncio.get_event_loop().create_future()
    def _ensure_debug_daemon(self, *args, **kwargs) -> asyncio.Task:
        if not self.debug_logs_enabled:
            self._daemon = asyncio.get_event_loop().create_future()
        if not hasattr(self, '_daemon') or self._daemon is None:
            self._daemon = self._start_debug_daemon(*args, **kwargs)
            self._daemon.add_done_callback(self._stop_debug_daemon)
        return self._daemon
    def _stop_debug_daemon(self, t: Optional[asyncio.Task] = None) -> None:
        if t and t != self._daemon:
            raise ValueError(f"{t} is not {self._daemon}")
        self._daemon.cancel()
        self._daemon = None
