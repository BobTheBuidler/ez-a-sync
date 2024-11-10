"""
This module provides an enhanced version of asyncio.Event with additional debug logging to help detect deadlocks.
"""

import asyncio
import sys

from a_sync._typing import *
from a_sync.primitives._debug import _DebugDaemonMixin


class Event(asyncio.Event, _DebugDaemonMixin):
    """
    An asyncio.Event with additional debug logging to help detect deadlocks.

    This event class extends asyncio.Event by adding debug logging capabilities. It logs
    detailed information about the event state and waiters, which can be useful for
    diagnosing and debugging potential deadlocks.
    """

    _value: bool
    _loop: asyncio.AbstractEventLoop
    _waiters: Deque["asyncio.Future[None]"]
    if sys.version_info >= (3, 10):
        __slots__ = "_value", "_waiters", "_debug_daemon_interval"
    else:
        __slots__ = "_value", "_loop", "_waiters", "_debug_daemon_interval"

    def __init__(
        self,
        name: str = "",
        debug_daemon_interval: int = 300,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """
        Initializes the Event.

        Args:
            name (str): An optional name for the event, used in debug logs.
            debug_daemon_interval (int): The interval in seconds for the debug daemon to log information.
            loop (Optional[asyncio.AbstractEventLoop]): The event loop to use.
        """
        if sys.version_info >= (3, 10):
            super().__init__()
        else:
            super().__init__(loop=loop)
        self._name = name
        # backwards compatability
        if hasattr(self, "_loop"):
            self._loop = self._loop or asyncio.get_event_loop()
        self._debug_daemon_interval = debug_daemon_interval

    def __repr__(self) -> str:
        label = f"name={self._name}" if self._name else "object"
        status = "set" if self._value else "unset"
        if self._waiters:
            status += f", waiters:{len(self._waiters)}"
        return f"<{self.__class__.__module__}.{self.__class__.__name__} {label} at {hex(id(self))} [{status}]>"

    async def wait(self) -> Literal[True]:
        """
        Wait until the event is set.

        Returns:
            True when the event is set.
        """
        if self.is_set():
            return True
        self._ensure_debug_daemon()
        return await super().wait()

    async def _debug_daemon(self) -> None:
        """
        Periodically logs debug information about the event state and waiters.
        """
        weakself = weakref.ref(self)
        del self  # no need to hold a reference here
        while (self := weakself()) and not self.is_set():
            del self  # no need to hold a reference here
            await asyncio.sleep(self._debug_daemon_interval)
            if (self := weakself()) and not self.is_set():
                self.logger.debug(
                    "Waiting for %s for %sm", self, round((time() - start) / 60, 2)
                )
