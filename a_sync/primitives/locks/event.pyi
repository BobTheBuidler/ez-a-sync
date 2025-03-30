from a_sync._typing import *
import asyncio
from a_sync.primitives._debug import _DebugDaemonMixin

class CythonEvent(asyncio.Event, _DebugDaemonMixin):
    """
    An asyncio.Event with additional debug logging to help detect deadlocks.

    This event class extends asyncio.Event by adding debug logging capabilities. It logs
    detailed information about the event state and waiters, which can be useful for
    diagnosing and debugging potential deadlocks.
    """

    def __init__(
        self,
        name: str = "",
        debug_daemon_interval: int = 300,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """
        Initializes the Event.

        Args:
            name (str): An optional name for the event, used in debug logs.
            debug_daemon_interval (int): The interval in seconds for the debug daemon to log information.
            loop (Optional[asyncio.AbstractEventLoop]): The event loop to use.
        """

    async def wait(self) -> Literal[True]:
        """
        Wait until the event is set.

        Returns:
            True when the event is set.
        """

    async def _debug_daemon(self) -> None:
        """
        Periodically logs debug information about the event state and waiters.

        This code will only run if `self.logger.isEnabledFor(logging.DEBUG)` is True. You do not need to include any level checks in your custom implementations.
        """
