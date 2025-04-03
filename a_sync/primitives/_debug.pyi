"""
This module provides a mixin class used to facilitate the creation of debugging daemons in subclasses.

The mixin provides a framework for managing a debug daemon task, which can be used to emit rich debug logs from subclass instances whenever debug logging is enabled. Subclasses must implement the specific logging behavior.
"""

from asyncio import AbstractEventLoop, Future

from a_sync.primitives._loggable import _LoggerMixin

class _LoopBoundMixin(_LoggerMixin):
    def __init__(self, *, loop=None): ...
    @property
    def _loop(self) -> AbstractEventLoop: ...
    def _get_loop(self) -> AbstractEventLoop: ...

class _DebugDaemonMixin(_LoopBoundMixin):
    """
    A mixin class that provides a framework for debugging capabilities using a daemon task.

    This mixin sets up the structure for managing a debug daemon task. Subclasses are responsible for implementing the specific behavior of the daemon, including any logging functionality.

    See Also:
        :class:`_LoggerMixin` for logging capabilities.
    """

    async def _debug_daemon(self, fut: Future, fn, *args, **kwargs) -> None:
        """
        Abstract method to define the debug daemon's behavior.

        Subclasses must implement this method to specify what the debug daemon should do, including any logging or monitoring tasks.

        This code will only run if `self.logger.isEnabledFor(logging.DEBUG)` is True. You do not need to include any level checks in your custom implementations.

        Args:
            fut: The future associated with the daemon.
            fn: The function to be debugged.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Examples:
            Implementing a simple debug daemon in a subclass:

            .. code-block:: python

                class MyDebugClass(_DebugDaemonMixin):
                    async def _debug_daemon(self, fut, fn, *args, **kwargs):
                        while not fut.done():
                            self.logger.debug("Debugging...")
                            await asyncio.sleep(1)
        """
        raise NotImplementedError
