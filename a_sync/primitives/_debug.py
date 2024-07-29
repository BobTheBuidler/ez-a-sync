"""
This module provides a mixin class for debugging purposes, integrating with asyncio's event loop.
The mixin ensures that a debugging daemon task is started if debug logging is enabled.
"""

import abc
import asyncio
from typing import Optional

from a_sync.primitives._loggable import _LoggerMixin

class _DebugDaemonMixin(_LoggerMixin, metaclass=abc.ABCMeta):
    """
    A mixin class that provides debugging capabilities using a daemon task.
    
    This mixin ensures that a debugging daemon task is started if debug logging is enabled.
    """
    __slots__ = "_daemon",

    @abc.abstractmethod
    async def _debug_daemon(self, fut: asyncio.Future, fn, *args, **kwargs) -> None:
        """
        Abstract method to define the debug daemon's behavior.
        
        Args:
            fut (asyncio.Future): The future associated with the daemon.
            fn: The function to be debugged.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
        """
        ...

    def _start_debug_daemon(self, *args, **kwargs) -> "asyncio.Future[None]":
        """
        Starts the debug daemon task if debug logging is enabled and the event loop is running.
        
        Args:
            *args: Positional arguments for the debug daemon.
            **kwargs: Keyword arguments for the debug daemon.
        
        Returns:
            asyncio.Future: A future representing the debug daemon task, or a blank future if the daemon cannot be created.
        """
        if self.debug_logs_enabled and asyncio.get_event_loop().is_running():
            return asyncio.create_task(self._debug_daemon(*args, **kwargs))
        # else we return a blank Future since we shouldn't or can't create the daemon
        return asyncio.get_event_loop().create_future()

    def _ensure_debug_daemon(self, *args, **kwargs) -> "asyncio.Future[None]":
        """
        Ensures that the debug daemon task is running.
        
        Args:
            *args: Positional arguments for the debug daemon.
            **kwargs: Keyword arguments for the debug daemon.
        
        Returns:
            asyncio.Future: The future representing the debug daemon task.
        """
        if not self.debug_logs_enabled:
            self._daemon = asyncio.get_event_loop().create_future()
        if not hasattr(self, '_daemon') or self._daemon is None:
            self._daemon = self._start_debug_daemon(*args, **kwargs)
            self._daemon.add_done_callback(self._stop_debug_daemon)
        return self._daemon

    def _stop_debug_daemon(self, t: Optional[asyncio.Task] = None) -> None:
        """
        Stops the debug daemon task.
        
        Args:
            t (Optional[asyncio.Task]): The task to be stopped. If not the current daemon, raises an error.
        """
        if t and t != self._daemon:
            raise ValueError(f"{t} is not {self._daemon}")
        self._daemon.cancel()
        self._daemon = None
