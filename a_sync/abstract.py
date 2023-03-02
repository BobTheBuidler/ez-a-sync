
import abc
from typing import Union

from a_sync import _flags, _kwargs, exceptions, modifiers
from a_sync._meta import ASyncMeta
from a_sync._typing import *


class ASyncABC(metaclass=ASyncMeta):

    ##################################
    # Concrete Methods (overridable) #
    ##################################

    def __a_sync_should_await__(self, kwargs: dict, force: Optional[Literal[True]] = None) -> bool:
        """Returns a boolean that indicates whether methods of 'instance' should be called as sync or async methods."""
        try:
            # Defer to kwargs always
            return self.__should_await_from_kwargs(kwargs)
        except exceptions.NoFlagsFound:
            # No flag found in kwargs, check for a flag attribute.
            return force if force else self.__should_await_from_instance

    @property
    def __should_await_from_instance(self) -> bool:
        """You can override this if you want."""
        return _flags.negate_if_necessary(self.__a_sync_flag_name__, self.__a_sync_flag_value__)
    
    def __should_await_from_kwargs(self, kwargs: dict) -> bool:
        """You can override this if you want."""
        return _kwargs.is_sync(kwargs, pop_flag=True)
    
    @classmethod
    def __a_sync_instance_will_be_sync__(cls, kwargs: dict) -> bool:
        """You can override this if you want."""
        try:
            return _kwargs.is_sync(kwargs)
        except exceptions.NoFlagsFound:
            return cls.__a_sync_default_mode__  # type: ignore [return-value]

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
    
    @abc.abstractclassmethod  # type: ignore [misc]
    @abc.abstractproperty
    def __a_sync_default_mode__(cls) -> bool:
        ...