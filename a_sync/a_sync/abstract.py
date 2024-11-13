"""
This module provides an abstract base class for defining asynchronous and synchronous behavior.

The ASyncABC class uses the ASyncMeta metaclass to automatically wrap its methods
with asynchronous or synchronous behavior based on flags. Subclasses must
implement the abstract methods to define the flag name, flag value, and
default mode for asynchronous or synchronous execution.

Note: It is recommended to use ASyncGenericBase for most use cases. This class
is intended for more custom implementations if necessary.
"""

import abc
import functools
import logging

from a_sync import exceptions
from a_sync._typing import *
from a_sync.a_sync import _flags, _kwargs, modifiers
from a_sync.a_sync._meta import ASyncMeta
from a_sync.exceptions import NoFlagsFound

logger = logging.getLogger(__name__)


class ASyncABC(metaclass=ASyncMeta):
    """Abstract Base Class for defining asynchronous and synchronous behavior.

    This class uses the ASyncMeta metaclass to automatically wrap its methods
    with asynchronous or synchronous behavior based on flags. Subclasses must
    implement the abstract methods to define the flag name, flag value, and
    default mode for asynchronous or synchronous execution.
    """

    ##################################
    # Concrete Methods (overridable) #
    ##################################

    def __a_sync_should_await__(self, kwargs: dict) -> bool:
        """Determines if methods should be called asynchronously.

        This method first checks the provided keyword arguments for flags
        indicating the desired execution mode. If no flags are found, it
        defaults to the instance's asynchronous flag.

        Args:
            kwargs: A dictionary of keyword arguments to check for flags.
        """
        try:
            return self.__a_sync_should_await_from_kwargs__(kwargs)
        except exceptions.NoFlagsFound:
            return self.__a_sync_instance_should_await__

    @functools.cached_property
    def __a_sync_instance_should_await__(self) -> bool:
        """Indicates if the instance should default to asynchronous execution.

        This property can be overridden if dynamic behavior is needed. For
        instance, to allow hot-swapping of instance modes, redefine this as a
        non-cached property.
        """
        return _flags.negate_if_necessary(
            self.__a_sync_flag_name__, self.__a_sync_flag_value__
        )

    def __a_sync_should_await_from_kwargs__(self, kwargs: dict) -> bool:
        """Determines execution mode from keyword arguments.

        This method can be overridden to customize how flags are extracted
        from keyword arguments.

        Args:
            kwargs: A dictionary of keyword arguments to check for flags.

        Raises:
            NoFlagsFound: If no valid flags are found in the keyword arguments.
        """
        if flag := _kwargs.get_flag_name(kwargs):
            return _kwargs.is_sync(flag, kwargs, pop_flag=True)  # type: ignore [arg-type]
        raise NoFlagsFound("kwargs", kwargs.keys())

    @classmethod
    def __a_sync_instance_will_be_sync__(cls, args: tuple, kwargs: dict) -> bool:
        """Determines if a new instance will be synchronous.

        This method checks the constructor's signature against provided
        keyword arguments to determine the execution mode for the new instance.

        Args:
            args: A tuple of positional arguments for the instance.
            kwargs: A dictionary of keyword arguments for the instance.
        """
        logger.debug(
            "checking `%s.%s.__init__` signature against provided kwargs to determine a_sync mode for the new instance",
            cls.__module__,
            cls.__name__,
        )
        if flag := _kwargs.get_flag_name(kwargs):
            sync = _kwargs.is_sync(flag, kwargs)  # type: ignore [arg-type]
            logger.debug(
                "kwargs indicate the new instance created with args %s %s is %ssynchronous",
                args,
                kwargs,
                "a" if sync is False else "",
            )
            return sync
        logger.debug(
            "No valid flags found in kwargs, checking class definition for defined default"
        )
        return cls.__a_sync_default_mode__()  # type: ignore [arg-type]

    ######################################
    # Concrete Methods (non-overridable) #
    ######################################

    @property
    def __a_sync_modifiers__(self: "ASyncABC") -> ModifierKwargs:
        """Retrieves modifiers for the instance.

        This method should not be overridden. It returns the modifiers
        associated with the instance, which are used to customize behavior.
        """
        return modifiers.get_modifiers_from(self)

    ####################
    # Abstract Methods #
    ####################

    @property
    @abc.abstractmethod
    def __a_sync_flag_name__(self) -> str:
        """Abstract property for the flag name.

        Subclasses must implement this property to return the name of the flag
        used to determine execution mode.
        """

    @property
    @abc.abstractmethod
    def __a_sync_flag_value__(self) -> bool:
        """Abstract property for the flag value.

        Subclasses must implement this property to return the value of the flag
        indicating the default execution mode.
        """

    @classmethod
    @abc.abstractmethod  # type: ignore [arg-type, misc]
    def __a_sync_default_mode__(cls) -> bool:  # type: ignore [empty-body]
        """Abstract class method for the default execution mode.

        Subclasses must implement this method to return the default execution
        mode (synchronous or asynchronous) for instances of the class.
        """
