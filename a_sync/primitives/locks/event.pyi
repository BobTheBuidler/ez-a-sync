from a_sync._typing import *
import asyncio
from a_sync.primitives._debug import _DebugDaemonMixin

class CythonEvent(asyncio.Event, _DebugDaemonMixin):
    """
    An asyncio.Event with additional debug logging to help detect deadlocks.

    This event class extends :class:`asyncio.Event` by adding debug logging capabilities.
    It logs detailed information about the event state and waiters, which can be useful for
    diagnosing and debugging potential deadlocks.

    See Also:
        :class:`asyncio.Event`
        :class:`a_sync.primitives._debug._DebugDaemonMixin`
    """

    def __init__(
        self,
        name: str = "",
        debug_daemon_interval: int = 300,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """
        Initializes the event.

        Args:
            name (str): An optional name for the event, used in debug logs.
            debug_daemon_interval (int): The interval in seconds for the debug daemon to log information.
            loop (Optional[asyncio.AbstractEventLoop]): **Not supported.** Passing a loop will cause a :class:`TypeError`.

        Examples:
            >>> event = CythonEvent(name="TestEvent", debug_daemon_interval=100)
            >>> # Attempting to pass a loop will raise a TypeError:
            >>> import asyncio
            >>> loop = asyncio.get_event_loop()
            >>> CythonEvent(loop=loop)  # Raises TypeError

        See Also:
            :class:`asyncio.Event`
        """

    async def wait(self) -> Literal[True]:
        """
        Wait until the event is set.

        Returns:
            True when the event is set.

        Examples:
            >>> event = CythonEvent()
            >>> # In an asynchronous context:
            >>> result = await event.wait()
            >>> print(result)
            True

        See Also:
            :meth:`asyncio.Event.wait`
        """

    async def _debug_daemon(self) -> None:
        """
        Periodically logs debug information about the event state and waiters during debug mode.

        This method is intended to be overridden by subclasses. Its implementation should
        perform continuous debug logging using the associated debug logger while the provided
        future is not completed.

        Args:
            fut: The future object associated with the debug daemon.
            fn: The function to be debugged.
            *args: Additional positional arguments to pass to the debug function.
            **kwargs: Additional keyword arguments to pass to the debug function.

        Examples:
            >>> class MyEvent(CythonEvent):
            ...     async def _debug_daemon(self, fut, fn, *args, **kwargs):
            ...         while not fut.done():
            ...             self.logger.debug("Waiting for event...")
            ...             await asyncio.sleep(1)
            >>> event = MyEvent(name="TestEvent")
            >>> # When the logger’s debug level is enabled, _debug_daemon will be invoked automatically.
            >>> # In practice, use a testing framework to simulate and verify the debug daemon behavior.

        Note:
            This method will only be scheduled if :attr:`logger.isEnabledFor(logging.DEBUG)` is True.
            You do not need to perform additional level checks in your custom implementation.

        See Also:
            :meth:`a_sync.primitives._debug._DebugDaemonMixin._start_debug_daemon`
        """