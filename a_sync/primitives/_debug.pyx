"""
This module provides a mixin class used to facilitate the creation of debugging daemons in subclasses.

It supplies base functionality for binding an event loop and for managing a daemon task for debug logging.
See Also:
    :func:`~a_sync.a_sync._helpers.get_event_loop`
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
    """Base mixin for objects that require binding to an asyncio event loop.

    The event loop associated with an instance is determined automatically at first use.
    Note:
        The ``loop`` parameter is no longer supported. Any attempt to supply a loop (e.g. ``MyClass(loop=some_loop)``)
        will raise a ``TypeError``.
    
    Examples:
        >>> class MyDebugClass(_LoopBoundMixin):
        ...     pass
        >>> import asyncio
        >>> loop = asyncio.get_event_loop()
        >>> MyDebugClass(loop=loop)
        Traceback (most recent call last):
          ...
        TypeError: The loop parameter is not supported. As of 3.10, the *loop* parameter was removed from MyDebugClass() since it is no longer necessary.

    See Also:
        :func:`~a_sync.a_sync._helpers.get_event_loop`
    """
    def __cinit__(self):
        self._LoopBoundMixin__loop = None

    def __init__(self, *, loop=None):
        """Initialize the loop-bound object.

        Keyword Args:
            loop: This parameter is not supported and must be omitted.

        Raises:
            TypeError: If a non-None value is provided for the loop parameter.

        Examples:
            >>> class MyDebugClass(_LoopBoundMixin):
            ...     pass
            >>> MyDebugClass()  # Proper usage.
            <MyDebugClass ...>
            >>> MyDebugClass(loop=object())
            Traceback (most recent call last):
              ...
            TypeError: The loop parameter is not supported. As of 3.10, the *loop* parameter was removed from MyDebugClass() since it is no longer necessary.
        """
        if loop is not None:
            raise TypeError(
                'The loop parameter is not supported. '
                'As of 3.10, the *loop* parameter was removed'
                '{}() since it is no longer necessary.'.format(type(self).__name__)
            )

    cpdef object _get_loop(self):
        return self._c_get_loop()

    cdef object _c_get_loop(self):
        """Retrieve and validate the event loop associated with the current thread.

        This method obtains the currently running event loop and binds it to the instance
        if no loop has been previously bound. If the instance already has a bound loop, but the
        current running loop differs from it, a RuntimeError is raised.

        Examples:
            >>> import asyncio
            >>> instance = MyDebugClass()
            >>> current_loop = asyncio.get_event_loop()
            >>> # First call binds current_loop to the instance.
            >>> bound_loop = instance._c_get_loop()  
            >>> assert bound_loop is current_loop
            >>> # In a different context if a different loop is running:
            >>> # instance._c_get_loop() will raise a RuntimeError.

        See Also:
            :func:`~a_sync.a_sync._helpers.get_event_loop`
        """
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

    This mixin sets up the structure for managing a debug daemon task.
    Subclasses must implement the specific behavior of the daemon by overriding
    the _debug_daemon() method.

    Note:
        The event loop associated with the instance is determined automatically at first use.
        If the currently running event loop does not match the loop bound to the instance,
        a RuntimeError is raised indicating that the object is bound to a different event loop.

    Examples:
        Implementing a simple debug daemon in a subclass:

        .. code-block:: python

            import asyncio

            class MyDebugClass(_DebugDaemonMixin):
                async def _debug_daemon(self, fut, fn, *args, **kwargs):
                    while not fut.done():
                        self.logger.debug("Debugging...")
                        await asyncio.sleep(1)

        In the above example, the debug daemon will run as long as debug logging is enabled
        and the event loop remains consistent.

    See Also:
        :class:`_LoggerMixin`,
        :func:`~a_sync.a_sync._helpers.get_event_loop`
    """
    
    def __cinit__(self):
        self._has_daemon = False
        self._LoopBoundMixin__loop = None

    async def _debug_daemon(self, fut: Future, fn, *args, **kwargs) -> None:
        """
        Abstract method to define the debug daemon's behavior.

        Subclasses must override this method to specify what the debug daemon should do,
        including any logging or monitoring tasks. This method is only invoked if debug logging
        is enabled. There is no need to perform further level checks within custom implementations.

        Args:
            fut: The Future associated with the daemon.
            fn: The function to be debugged.
            *args: Positional arguments for the debug task.
            **kwargs: Keyword arguments for the debug task.

        Examples:
            .. code-block:: python

                class MyDebugClass(_DebugDaemonMixin):
                    async def _debug_daemon(self, fut, fn, *args, **kwargs):
                        while not fut.done():
                            self.logger.debug("Debugging...")
                            await asyncio.sleep(1)

        Raises:
            NotImplementedError: Always, in the base mixin.
        """
        raise NotImplementedError

    def _start_debug_daemon(self, *args, **kwargs) -> "Future[None]":
        """
        Starts the debug daemon task if debug logging is enabled and the event loop is running.

        This method checks whether debug logging is enabled and verifies that the event loop
        obtained via :meth:`_c_get_loop` is running. If both conditions are met, it starts the
        debug daemon task asynchronously. Otherwise, a dummy future is returned.

        Args:
            *args: Positional arguments for the debug daemon.
            **kwargs: Keyword arguments for the debug daemon.

        Returns:
            A Future representing the debug daemon task, or a dummy future if conditions are not met.

        Examples:
            .. code-block:: python

                my_instance = MyDebugClass()
                task = my_instance._start_debug_daemon()
                # task will be an asyncio Task if debug logging is enabled
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

        This method verifies if the debug daemon is already running and starts it if necessary.
        If debug logging is not enabled, it sets the daemon to a dummy future.

        Args:
            *args: Positional arguments for the debug daemon.
            **kwargs: Keyword arguments for the debug daemon.

        Examples:
            .. code-block:: python

                my_instance = MyDebugClass()
                my_instance._ensure_debug_daemon()
        See Also:
            :meth:`_start_debug_daemon`
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

        This method cancels the debug daemon task if it is running.
        It raises a ValueError if the task supplied for stopping is not the current daemon.

        Args:
            t (optional): The task to be stopped, if specified.

        Examples:
            .. code-block:: python

                my_instance = MyDebugClass()
                my_instance._stop_debug_daemon()

        See Also:
            :meth:`_ensure_debug_daemon`
        """
        if t and t != self._daemon:
            raise ValueError(f"{t} is not {self._daemon}")
        t.cancel()
        self._daemon = None
        self._has_daemon = False