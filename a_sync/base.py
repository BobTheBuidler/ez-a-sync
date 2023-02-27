
from a_sync import _flags, _kwargs, exceptions
from a_sync._meta import ASyncMeta


class ASyncBase(metaclass=ASyncMeta):
    """Inherit from this class to a-syncify all of your bound methods."""
    pass

    @property
    def __a_sync_flag_name(self) -> str:
        present_flags = [flag for flag in _flags.VIABLE_FLAGS if hasattr(self, flag)]
        if len(present_flags) == 0:
            raise exceptions.NoFlagsFound(self)
        if len(present_flags) > 1:
            raise exceptions.TooManyFlags(self, present_flags)
        return present_flags[0]
    
    @property
    def __a_sync_flag_value(self) -> bool:
        flag = self.__a_sync_flag_name
        flag_value = getattr(self, flag)
        if not isinstance(flag_value, bool):
            raise exceptions.InvalidFlagValue(flag, flag_value)
        return flag_value
    
    @property
    def __should_await_from_instance(self) -> bool:
        return _flags.negate_if_necessary(self.__a_sync_flag_name, self.__a_sync_flag_value)
    
    def __should_await_from_kwargs(self, kwargs: dict) -> bool:
        flag = _kwargs.get_flag_name(kwargs)
        flag_value = _kwargs.pop_flag_value(flag, kwargs)
        return _flags.negate_if_necessary(flag, flag_value)
    
    def _should_await(self, kwargs: dict) -> bool:
        """Returns a boolean that indicates whether methods of 'instance' should be called as sync or async methods."""
        try:
            # Defer to kwargs always
            return self.__should_await_from_kwargs(kwargs)
        except exceptions.NoFlagsFound:
            # No flag found in kwargs, check for a flag attribute.
            return self.__should_await_from_instance
