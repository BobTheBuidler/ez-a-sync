"""
This module provides a mixin class used to facilitate the creation of debugging daemons in subclasses.

The mixin provides a framework for managing a debug daemon task, which can be used to emit rich debug logs from subclass instances whenever debug logging is enabled. Subclasses must implement the specific logging behavior.
"""
import abc
from a_sync.primitives._loggable import _LoggerMixin

class _DebugDaemonMixin(_LoggerMixin):
    """
    A mixin class that provides a framework for debugging capabilities using a daemon task.

    This mixin sets up the structure for managing a debug daemon task. Subclasses are responsible for implementing the specific behavior of the daemon, including any logging functionality.

    See Also:
        :class:`_LoggerMixin` for logging capabilities.
    """
