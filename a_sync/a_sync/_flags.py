"""
This module provides functionality for handling synchronous and asynchronous flags
in the ez-a-sync library.

ez-a-sync uses 'flags' to indicate whether objects or function calls will be synchronous or asynchronous.

You can use any of the provided flags, whichever makes the most sense for your use case.

AFFIRMATIVE_FLAGS: Set of flags indicating synchronous behavior. Currently includes "sync".

NEGATIVE_FLAGS: Set of flags indicating asynchronous behavior. Currently includes "asynchronous".

VIABLE_FLAGS: Set of all valid flags, combining both synchronous and asynchronous indicators.
"""

from typing import Any

from a_sync import exceptions

AFFIRMATIVE_FLAGS = {"sync"}
"""Set of flags indicating synchronous behavior."""

NEGATIVE_FLAGS = {"asynchronous"}
"""Set of flags indicating asynchronous behavior."""

VIABLE_FLAGS = AFFIRMATIVE_FLAGS | NEGATIVE_FLAGS
"""Set of all valid flags."""


def negate_if_necessary(flag: str, flag_value: bool) -> bool:
    """Negate the flag value if necessary based on the flag type.

    Args:
        flag: The flag to check.
        flag_value: The value of the flag.

    Returns:
        The potentially negated flag value.

    Raises:
        exceptions.InvalidFlag: If the flag is not recognized.
    """
    validate_flag_value(flag, flag_value)
    if flag in AFFIRMATIVE_FLAGS:
        return bool(flag_value)
    elif flag in NEGATIVE_FLAGS:
        return bool(not flag_value)
    raise exceptions.InvalidFlag(flag)


def validate_flag_value(flag: str, flag_value: Any) -> bool:
    """
    Validate that the flag value is a boolean.

    Args:
        flag: The flag being validated.
        flag_value: The value to validate.

    Returns:
        The validated flag value.

    Raises:
        exceptions.InvalidFlagValue: If the flag value is not a boolean.
    """
    if not isinstance(flag_value, bool):
        raise exceptions.InvalidFlagValue(flag, flag_value)
    return flag_value
