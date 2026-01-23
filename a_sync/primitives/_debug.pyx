"""
This module provides a mixin class used to facilitate the creation of debugging daemons in subclasses.

The mixin provides a framework for managing a debug daemon task, which can be used to emit rich debug logs from subclass instances whenever debug logging is enabled. Subclasses must implement the specific logging behavior.
"""

import asyncio
import os
import threading
import typing

from a_sync.a_sync._helpers cimport get_event_loop
from a_sync.asyncio.create_task cimport ccreate_task_simple
from a_sync.primitives._loggable cimport _LoggerMixin


# cdef asyncio
cdef object AbstractEventLoop = asyncio.AbstractEventLoop
cdef object Future = asyncio.Future
cdef object Task = asyncio.Task
cdef object _running_loop = asyncio.events._running_loop
del asyncio

# cdef os
cdef object getpid = os.getpid
del os

# cdef typing
cdef object Optional = typing.Optional
del typing


cdef public object _global_lock = threading.Lock()
del threading


cdef object _get_running_loop():
    """Return the running event loop or None.

    This is a low-level function intended to be used by event loops.
    This function is thread-specific.
    """
    cdef object running_loop, pid
    running_loop, pid = _running_loop.loop_pid
    if running_loop is not None and <int>pid == <int>getpid():
        return running_loop


cdef class _LoopBoundMixin(_LoggerMixin):
    def __cinit__(self):
        self._LoopBoundMixin__loop = None
    def __init__(self, *, loop=None):
        if loop is not None:
            raise TypeError(
                'The loop parameter is not supported. '
                'As of 3.10, the *loop* parameter was removed'
                '{}() since it is no longer necessary.'.format(type(self).__name__)
            )
    @property
    def _loop(self) -> AbstractEventLoop:
        return self._LoopBoundMixin__loop
    @_loop.setter
    def _loop(self, loop: AbstractEventLoop):
        self._LoopBoundMixin__loop = loop
    cpdef object _get_loop(self):
        return self._c_get_loop()
    cdef object _c_get_loop(self):
        cdef object loop = _get_running_loop()
        if self._LoopBoundMixin__loop is None:
            with _global_lock:
                if self._LoopBoundMixin__loop is None:
                    self._LoopBoundMixin__loop = loop
        if loop is None:
            return get_event_loop()
        elif loop is not self._LoopBoundMixin__loop:
            raise RuntimeError(
                f'{self!r} is bound to a different event loop', 
                "running loop: ".format(loop), 
                "bound to: ".format(self._LoopBoundMixin__loop),
            )
        return loop


cdef class _DebugDaemonMixin(_LoopBoundMixin):
    """
    A mixin class that provides a framework for debugging capabilities using a daemon task.

    This mixin sets up the structure for managing a debug daemon task. Subclasses are responsible for implementing the specific behavior of the daemon, including any logging functionality.

    See Also:
        :class:`_LoggerMixin` for logging capabilities.
    """
    
    def __cinit__(self):
        self._has_daemon = False
        self._LoopBoundMixin__loop = None

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

    def _start_debug_daemon(self, *args, **kwargs) -> "Future[None]":
        """
        Starts the debug daemon task if debug logging is enabled and the event loop is running.

        This method checks if debug logging is enabled and if the event loop is running. If both conditions are met, it starts the debug daemon task.

        Args:
            *args: Positional arguments for the debug daemon.
            **kwargs: Keyword arguments for the debug daemon.

        Returns:
            The debug daemon task as an asyncio.Task, or a dummy future if debug logs are not enabled or if the daemon cannot be created.

        Examples:
            Starting the debug daemon:

            .. code-block:: python

                my_instance = MyDebugClass()
                my_instance._start_debug_daemon()

        See Also:
            :meth:`_ensure_debug_daemon` for ensuring the daemon is running.
        """
        return self._c_start_debug_daemon(args, kwargs)
    
    cdef object _c_start_debug_daemon(self, tuple[object] args, dict[str, object] kwargs):
        cdef object loop = self._c_get_loop()
        if self.check_debug_logs_enabled() and loop.is_running():
            return ccreate_task_simple(self._debug_daemon(*args, **kwargs))
        return loop.create_future()

    def _ensure_debug_daemon(self, *args, **kwargs) -> None:
        """
        Ensures that the debug daemon task is running.

        This method checks if the debug daemon is already running and starts it if necessary. If debug logging is not enabled, it sets the daemon to a dummy future.

        Args:
            *args: Positional arguments for the debug daemon.
            **kwargs: Keyword arguments for the debug daemon.

        Returns:
            Either the debug daemon task or a dummy future if debug logging is not enabled.

        Examples:
            Ensuring the debug daemon is running:

            .. code-block:: python

                my_instance = MyDebugClass()
                my_instance._ensure_debug_daemon()

        See Also:
            :meth:`_start_debug_daemon` for starting the daemon.
        """
        self._c_ensure_debug_daemon(args, kwargs)
    
    cdef void _c_ensure_debug_daemon(self, tuple[object] args, dict[str, object] kwargs):
        if self._has_daemon:
            return
        
        if self.check_debug_logs_enabled():
            daemon = self._c_start_debug_daemon(args, kwargs)
            daemon.add_done_callback(self._stop_debug_daemon)
            self._daemon = daemon
        else:
            self._daemon = self._c_get_loop().create_future()
            
        self._has_daemon = True

    def _stop_debug_daemon(self, t: Optional[Task] = None) -> None:
        """
        Stops the debug daemon task.

        This method cancels the debug daemon task if it is running. Raises a ValueError if the task to be stopped is not the current daemon.

        Args:
            t (optional): The task to be stopped, if any.

        Raises:
            ValueError: If `t` is not the current daemon.

        Examples:
            Stopping the debug daemon:

            .. code-block:: python

                my_instance = MyDebugClass()
                my_instance._stop_debug_daemon()

        See Also:
            :meth:`_ensure_debug_daemon` for ensuring the daemon is running.
        """
        if t and t != self._daemon:
            raise ValueError(f"{t} is not {self._daemon}")
        t.cancel()
        self._daemon = None
        self._has_daemon = False
