
import inspect
import logging
from functools import cached_property
from typing import Optional

from a_sync import _flags, exceptions
from a_sync.abstract import ASyncABC


logger = logging.getLogger(__name__)

class ASyncGenericBase(ASyncABC):
    """
    Inherit from this class to a-syncify all of your bound methods.
    Allows for the use of a variety of flags out-of-box.
    You can choose which flag(s) work best for your subclass implementation.
    """
    @cached_property
    def __a_sync_flag_name__(self) -> str:
        logger.debug(f"checking a_sync flag for {self}")
        try:
            flag = self.__get_a_sync_flag_name_from_signature()
        except exceptions.ASyncFlagException:
            # We can't get the flag name from the __init__ signature,
            # but maybe the implementation sets the flag somewhere else.
            # Let's check the instance's atributes
            logger.debug(f"unable to find flag name using `{self.__class__.__name__}.__init__` signature, checking for flag attributes defined on {self}")
            present_flags = [flag for flag in _flags.VIABLE_FLAGS if hasattr(self, flag)]
            if len(present_flags) == 0:
                raise exceptions.NoFlagsFound(self)
            if len(present_flags) > 1:
                raise exceptions.TooManyFlags(self, present_flags)
            flag = present_flags[0]
        if not isinstance(flag, str):
            raise exceptions.InvalidFlag(flag)
        return flag
        
    @property  # This property is not cached so you can 
    def __a_sync_flag_value__(self) -> bool:
        flag = self.__a_sync_flag_name__
        flag_value = getattr(self, flag)
        if not isinstance(flag_value, bool):
            raise exceptions.InvalidFlagValue(flag, flag_value)
        logger.debug(f'`{self}.{flag}` is currently {flag_value}')
        return flag_value

    @classmethod  # type: ignore [misc]
    def __a_sync_default_mode__(cls) -> bool:
        flag = cls.__get_a_sync_flag_name_from_signature()
        flag_value = cls.__a_sync_flag_default_value_from_signature()
        sync = _flags.negate_if_necessary(flag, flag_value)  # type: ignore [arg-type]
        logger.debug(f"`{cls}.{flag}` indicates default mode is {'a' if sync is False else ''}synchronous")
        return sync
    
    @classmethod
    def __get_a_sync_flag_name_from_signature(cls) -> Optional[str]:
        logger.debug(f"Searching for flags defined on {cls}")
        if cls.__name__ == "ASyncGenericBase":
            logger.debug(f"There are no flags defined on the base class, this is expected. Skipping.")
            return None
        parameters = inspect.signature(cls.__init__).parameters
        logger.debug(f"parameters: {parameters}")
        present_flags = [flag for flag in _flags.VIABLE_FLAGS if flag in parameters]
        if len(present_flags) == 0:
            logger.debug(f"There are too many flags defined on {cls}")
            raise exceptions.NoFlagsFound(cls, parameters.keys())
        if len(present_flags) > 1:
            logger.debug(f"There are too many flags defined on {cls}")
            raise exceptions.TooManyFlags(cls, present_flags)
        flag = present_flags[0]
        logger.debug(f"found flag {flag}")
        return flag

    @classmethod  # type: ignore [misc]
    def __a_sync_flag_default_value_from_signature(cls) -> bool:
        logger.debug(f"checking `__init__` signature for default {cls} a_sync flag value")
        signature = inspect.signature(cls.__init__)
        flag = cls.__get_a_sync_flag_name_from_signature()
        flag_value = signature.parameters[flag].default
        if flag_value is inspect._empty:  # type: ignore [attr-defined]
            raise NotImplementedError(
                "The implementation for 'cls' uses an arg to specify sync mode, instead of a kwarg. We are unable to proceed. I suppose we can extend the code to accept positional arg flags if necessary"
            )
        logger.debug(f'{cls} defines {flag}, default value {flag_value}')
        return flag_value
