
from typing import Any

from a_sync import exceptions

AFFIRMATIVE_FLAGS = {'sync'}
NEGATIVE_FLAGS = {'asynchronous'}
VIABLE_FLAGS = AFFIRMATIVE_FLAGS | NEGATIVE_FLAGS

def negate_if_necessary(flag: str, flag_value: bool):
    if flag in AFFIRMATIVE_FLAGS:
        return bool(flag_value)
    elif flag in NEGATIVE_FLAGS:
        return bool(not flag_value)
    from a_sync.exceptions import InvalidFlag
    raise InvalidFlag(flag)

def validate_flag_value(flag: str, flag_value: Any) -> bool:
    if not isinstance(flag_value, bool):
        raise exceptions.InvalidFlagValue(flag, flag_value)
    return flag_value
