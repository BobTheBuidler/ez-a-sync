
import inspect

from a_sync import _flags, exceptions
from a_sync.abstract import ASyncABC


class ASyncGenericBase(ASyncABC):
    """
    Inherit from this class to a-syncify all of your bound methods.
    Allows for the use of a variety of flags out-of-box.
    You can choose which flag(s) work best for your subclass implementation.
    """
    @property
    def __a_sync_flag_name__(self) -> str:
        try:
            return self.__get_a_sync_flag_name_from_signature()
        except exceptions.ASyncFlagException:
            # We can't get the flag name from the __init__ signature,
            # but maybe the implementation sets the flag somewhere else.
            # Let's check the instance's atributes
            present_flags = [flag for flag in _flags.VIABLE_FLAGS if hasattr(self, flag)]
            if len(present_flags) == 0:
                raise exceptions.NoFlagsFound(self)
            if len(present_flags) > 1:
                raise exceptions.TooManyFlags(self, present_flags)
            return present_flags[0]
        
    @property
    def __a_sync_flag_value__(self) -> bool:
        flag = self.__a_sync_flag_name__
        if not isinstance(flag, str):
            raise TypeError(flag, type(flag))
        flag_value = getattr(self, flag)
        if not isinstance(flag_value, bool):
            raise exceptions.InvalidFlagValue(flag, flag_value)
        return flag_value

    @classmethod  # type: ignore [misc]
    @property
    def __a_sync_default_mode__(cls) -> bool:
        flag = cls.__get_a_sync_flag_name_from_signature()
        flag_value = cls.__a_sync_flag_default_value_from_signature
        return _flags.negate_if_necessary(flag, flag_value)  # type: ignore [arg-type]
    
    @classmethod
    #@property # TODO debug why making this into a classproperty breaks it
    def __get_a_sync_flag_name_from_signature(cls) -> str:
        signature = inspect.signature(cls.__init__)
        present_flags = [flag for flag in _flags.VIABLE_FLAGS if flag in signature.parameters]
        if len(present_flags) == 0:
            raise exceptions.NoFlagsFound(cls, signature.parameters.keys())
        if len(present_flags) > 1:
            raise exceptions.TooManyFlags(cls, present_flags)
        return present_flags[0]

    @classmethod  # type: ignore [misc]
    @property
    def __a_sync_flag_default_value_from_signature(cls) -> bool:
        signature = inspect.signature(cls.__init__)
        flag = cls.__get_a_sync_flag_name_from_signature()
        flag_value = signature.parameters[flag].default
        if flag_value is inspect._empty:  # type: ignore [attr-defined]
            raise Exception("The implementation for 'cls' uses an arg to specify sync mode, instead of a kwarg. We are unable to proceed. I suppose we can extend the code to accept positional arg flags if necessary")
        return _flags.validate_flag_value(flag, flag_value)
