import abc
from a_sync.primitives._loggable import _LoggerMixin

class _DebugDaemonMixin(_LoggerMixin, metaclass=abc.ABCMeta):
    """
    A mixin class that provides a framework for debugging capabilities using a daemon task.

    This mixin sets up the structure for managing a debug daemon task. Subclasses are responsible for implementing the specific behavior of the daemon, including any logging functionality.

    See Also:
        :class:`_LoggerMixin` for logging capabilities.
    """
