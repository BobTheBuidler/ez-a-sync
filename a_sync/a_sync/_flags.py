
from typing import Any

from a_sync import exceptions

AFFIRMATIVE_FLAGS = {'sync'}
NEGATIVE_FLAGS = {'asynchronous'}
VIABLE_FLAGS = AFFIRMATIVE_FLAGS | NEGATIVE_FLAGS

"""
A-Sync uses 'flags' to indicate whether objects / fn calls will be sync or async.
You can use any of the provided flags, whichever makes most sense for your use case.
"""

def negate_if_necessary(flag: str, flag_value: bool):
    validate_flag_value(flag, flag_value)
    if flag in AFFIRMATIVE_FLAGS:
        return bool(flag_value)
    elif flag in NEGATIVE_FLAGS:
        return bool(not flag_value)
    raise exceptions.InvalidFlag(flag)

def validate_flag_value(flag: str, flag_value: Any) -> bool:
    if not isinstance(flag_value, bool):
        raise exceptions.InvalidFlagValue(flag, flag_value)
    return flag_value
