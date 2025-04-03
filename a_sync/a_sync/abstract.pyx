"""
This module provides an abstract base class for defining asynchronous and synchronous behavior.

The :class:`ASyncABC` class uses the :class:`ASyncMeta` metaclass to facilitate the creation of classes
that can operate in both asynchronous and synchronous contexts. It provides concrete methods to determine
the execution mode based on flags and keyword arguments.

Note: It is recommended to use :class:`ASyncGenericBase` for most use cases. This class
is intended for more custom implementations if necessary.
"""

from abc import abstractmethod
from logging import getLogger
from typing import Dict, Any, Tuple

from a_sync._typing import *
from a_sync.a_sync._kwargs cimport get_flag_name, is_sync
from a_sync.a_sync._flags cimport validate_and_negate_if_necessary
from a_sync.a_sync._meta import ASyncMeta


cdef struct ShouldAwaitCache:
    bint is_cached
    bint value


logger = getLogger(__name__)

cdef object _logger_is_enabled = logger.isEnabledFor
cdef object _logger_log = logger._log
cdef object DEBUG = 10

cdef inline void _log_debug(str msg, tuple args):
    _logger_log(DEBUG, msg, args)

    
class ASyncABC(metaclass=ASyncMeta):
    """Abstract Base Class for defining asynchronous and synchronous behavior.

    This class provides methods to determine the execution mode based on flags and keyword arguments.
    It is designed to be subclassed, allowing developers to create classes that can be used in both
    synchronous and asynchronous contexts.
    
    See Also:
        - :class:`ASyncGenericBase`: A more user-friendly base class for creating dual-mode classes.
        - :class:`ASyncMeta`: Metaclass that facilitates asynchronous capabilities in class attributes.

    Examples:
        To create a class that inherits from `ASyncABC`, you need to implement the abstract methods
        and can override the concrete methods if needed.

        ```python
        class MyASyncClass(ASyncABC):
            @property
            def __a_sync_flag_name__(self) -> str:
                return "sync"

            @property
            def __a_sync_flag_value__(self) -> bool:
                return True

            @classmethod
            def __a_sync_default_mode__(cls) -> bool:
                return False
        ```

        In this example, `MyASyncClass` is a subclass of `ASyncABC` with custom implementations
        for the required abstract methods.
    """

    def __init__(self) -> None:
        cdef ShouldAwaitCache cache
        cache.is_cached = False
        cache.value = False
        self.__a_sync_should_await_cache__ = cache

    ##################################
    # Concrete Methods (overridable) #
    ##################################

    def __a_sync_should_await__(self, Dict[str, Any] kwargs) -> bint:
        """Determines if methods should be called asynchronously.

        This method first checks the provided keyword arguments for flags
        indicating the desired execution mode. If no flags are found, it
        defaults to the instance's asynchronous flag.

        Args:
            kwargs: A dictionary of keyword arguments to check for flags.

        Examples:
            >>> instance = MyASyncClass()
            >>> instance.__a_sync_should_await__({'sync': True})
            False
        """
        
        cdef str flag = get_flag_name(kwargs)
        if flag:
            return is_sync(flag, kwargs, pop_flag=True)
        
        cdef ShouldAwaitCache cache

        try:
            cache = self.__a_sync_should_await_cache__
        except AttributeError:
            raise RuntimeError(
                f"{self} has not been properly initialized. "
                f"Please ensure your `{type(self).__name__}.__init__` method calls `ASyncABC.__init__(self)`."
            )

        if not cache.is_cached:
            cache.value = validate_and_negate_if_necessary(
                self.__a_sync_flag_name__, self.__a_sync_flag_value__
            )
            cache.is_cached = True
            self.__a_sync_should_await_cache__ = cache
        return cache.value

    @property
    def __a_sync_instance_should_await__(self) -> bint:
        # TODO: refactor this out
        """Indicates if the instance should default to asynchronous execution.

        This property can be overridden if dynamic behavior is needed. For
        instance, to allow hot-swapping of instance modes, redefine this as a
        non-cached property.

        Examples:
            >>> instance = MyASyncClass()
            >>> instance.__a_sync_instance_should_await__
            True
        """
        cdef ShouldAwaitCache cache

        try:
            cache = self.__a_sync_should_await_cache__
        except AttributeError:
            raise RuntimeError(
                f"{self} has not been properly initialized. "
                f"Please ensure your `{type(self).__name__}.__init__` method calls `ASyncABC.__init__(self)`."
            )

        if not cache.is_cached:
            cache.value = validate_and_negate_if_necessary(
                self.__a_sync_flag_name__, self.__a_sync_flag_value__
            )
            cache.is_cached = True
            self.__a_sync_should_await_cache__ = cache
        return cache.value

    @classmethod
    def __a_sync_instance_will_be_sync__(cls, Tuple[Any, ...] args, Dict[str, Any] kwargs) -> bint:
        """Determines if a new instance will be synchronous.

        This method checks the constructor's signature against provided
        keyword arguments to determine the execution mode for the new instance.

        Args:
            args: A tuple of positional arguments for the instance.
            kwargs: A dictionary of keyword arguments for the instance.

        Examples:
            >>> MyASyncClass.__a_sync_instance_will_be_sync__((), {'sync': True})
            True
        """
        cdef bint debug_logs = _logger_is_enabled(DEBUG)
        
        if debug_logs:
            _log_debug(
                "checking `%s.%s.__init__` signature against provided kwargs to determine a_sync mode for the new instance",
                (cls.__module__, cls.__name__),
            )

        cdef str flag = get_flag_name(kwargs)
        if not debug_logs:
            return is_sync(flag, kwargs, pop_flag=False) if flag else cls.__a_sync_default_mode__()  # type: ignore [arg-type]
        
        if not flag:
            _log_debug(
                "No valid flags found in kwargs, checking class definition for defined default", ()
            )
            return cls.__a_sync_default_mode__()  # type: ignore [arg-type]

        cdef bint sync = is_sync(flag, kwargs, pop_flag=False)  # type: ignore [arg-type]
        _log_debug(
            "kwargs indicate the new instance created with args %s %s is %ssynchronous",
            (args, kwargs, "" if sync else "a"),
        )
        return sync

    ####################
    # Abstract Methods #
    ####################

    @property
    @abstractmethod
    def __a_sync_flag_name__(self) -> str:
        """Abstract property for the flag name.

        Subclasses must implement this property to return the name of the flag
        used to determine execution mode.
        """

    @property
    @abstractmethod
    def __a_sync_flag_value__(self) -> bool:
        """Abstract property for the flag value.

        Subclasses must implement this property to return the value of the flag
        indicating the default execution mode.
        """

    @classmethod
    @abstractmethod  # type: ignore [arg-type, misc]
    def __a_sync_default_mode__(cls) -> bool:  # type: ignore [empty-body]
        """Abstract class method for the default execution mode.

        Subclasses must implement this method to return the default execution
        mode (synchronous or asynchronous) for instances of the class.
        """
    
