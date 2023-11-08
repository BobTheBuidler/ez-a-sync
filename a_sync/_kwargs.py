
from typing import Optional

from a_sync import _flags, exceptions


def get_flag_name(kwargs: dict) -> Optional[str]:
    present_flags = [flag for flag in _flags.VIABLE_FLAGS if flag in kwargs]
    if len(present_flags) == 0:
        return None
    if len(present_flags) != 1:
        raise exceptions.TooManyFlags('kwargs', present_flags)
    return present_flags[0]

def is_sync(flag: str, kwargs: dict, pop_flag: bool = False) -> bool:
    flag_value = kwargs.pop(flag) if pop_flag else kwargs[flag]
    return _flags.negate_if_necessary(flag, flag_value)