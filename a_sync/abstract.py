
import abc
import functools
import logging

from a_sync import _flags, _kwargs, exceptions, modifiers
from a_sync._meta import ASyncMeta
from a_sync._typing import *
from a_sync.exceptions import NoFlagsFound

logger = logging.getLogger(__name__)

class ASyncABC(metaclass=ASyncMeta):

    ##################################
    # Concrete Methods (overridable) #
    ##################################

    def __a_sync_should_await__(self, kwargs: dict) -> bool:
        """Returns a boolean that indicates whether methods of 'instance' should be called as sync or async methods."""
        try:
            # Defer to kwargs always
            return self.__a_sync_should_await_from_kwargs__(kwargs)
        except exceptions.NoFlagsFound:
            # No flag found in kwargs, check for a flag attribute.
            return self.__a_sync_instance_should_await__

    @functools.cached_property
    def __a_sync_instance_should_await__(self) -> bool:
        """
        You can override this if you want. 
        If you want to be able to hotswap instance modes, you can redefine this as a non-cached property.
        """
        return _flags.negate_if_necessary(self.__a_sync_flag_name__, self.__a_sync_flag_value__)
    
    def __a_sync_should_await_from_kwargs__(self, kwargs: dict) -> bool:
        """You can override this if you want."""
        if flag := _kwargs.get_flag_name(kwargs):
            return _kwargs.is_sync(flag, kwargs, pop_flag=True)  # type: ignore [arg-type]
        raise NoFlagsFound("kwargs", kwargs.keys())
    
    @classmethod
    def __a_sync_instance_will_be_sync__(cls, args: tuple, kwargs: dict) -> bool:
        """You can override this if you want."""
        logger.debug("checking `%s.%s.__init__` signature against provided kwargs to determine a_sync mode for the new instance", cls.__module__, cls.__name__)
        if flag := _kwargs.get_flag_name(kwargs):
            sync = _kwargs.is_sync(flag, kwargs)  # type: ignore [arg-type]
            logger.debug("kwargs indicate the new instance created with args %s %s is %ssynchronous", args, kwargs, 'a' if sync is False else '')
            return sync
        logger.debug("No valid flags found in kwargs, checking class definition for defined default")
        return cls.__a_sync_default_mode__()  # type: ignore [arg-type]

    ######################################
    # Concrete Methods (non-overridable) #
    ######################################
    
    @property
    def __a_sync_modifiers__(self: "ASyncABC") -> ModifierKwargs:
        """You should not override this."""
        return modifiers.get_modifiers_from(self)

    ####################
    # Abstract Methods #
    ####################

    @abc.abstractproperty
    def __a_sync_flag_name__(self) -> str:
        pass
    
    @abc.abstractproperty
    def __a_sync_flag_value__(self) -> bool:
        pass
    
    @abc.abstractclassmethod  # type: ignore [arg-type, misc]
    def __a_sync_default_mode__(cls) -> bool:  # type: ignore [empty-body] 
                                                # mypy doesnt recognize this abc member
        pass
