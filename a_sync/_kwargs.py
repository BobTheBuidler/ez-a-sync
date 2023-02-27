
from a_sync import _flags, exceptions


def get_flag_name(kwargs: dict) -> str:
    present_flags = [flag for flag in _flags.VIABLE_FLAGS if flag in kwargs]
    if len(present_flags) == 0:
        raise exceptions.NoFlagsFound('kwargs', kwargs.keys())
    if len(present_flags) != 1:
        raise exceptions.TooManyFlags('kwargs', present_flags)
    return present_flags[0]

def get_flag_value(flag: str, kwargs: dict) -> bool:
    flag_value = kwargs[flag]
    return _flags.validate_flag_value(flag, flag_value)

def pop_flag_value(flag: str, kwargs: dict) -> bool:
    flag_value = kwargs.pop(flag)
    return _flags.validate_flag_value(flag, flag_value)
