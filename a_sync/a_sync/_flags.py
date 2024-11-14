"""
This module provides functionality for handling synchronous and asynchronous flags
in the ez-a-sync library.

ez-a-sync uses 'flags' to indicate whether objects or function calls will be synchronous or asynchronous.

You can use any of the provided flags, whichever makes the most sense for your use case.

AFFIRMATIVE_FLAGS: Set of flags indicating synchronous behavior. Currently includes "sync".

NEGATIVE_FLAGS: Set of flags indicating asynchronous behavior. Currently includes "asynchronous".

VIABLE_FLAGS: Set of all valid flags, combining both synchronous and asynchronous indicators.

Functions:
    - negate_if_necessary: Negates the flag value if necessary based on the flag type.
    - validate_flag_value: Validates that the flag value is a boolean.
"""

from typing import Any

from a_sync import exceptions

AFFIRMATIVE_FLAGS = {"sync"}
"""Set of flags indicating synchronous behavior.

Examples:
    >>> 'sync' in AFFIRMATIVE_FLAGS
    True

    >>> 'async' in AFFIRMATIVE_FLAGS
    False
"""

NEGATIVE_FLAGS = {"asynchronous"}
"""Set of flags indicating asynchronous behavior.

Examples:
    >>> 'asynchronous' in NEGATIVE_FLAGS
    True

    >>> 'sync' in NEGATIVE_FLAGS
    False
"""

VIABLE_FLAGS = AFFIRMATIVE_FLAGS | NEGATIVE_FLAGS
"""Set of all valid flags, combining both synchronous and asynchronous indicators.

A-Sync uses 'flags' to indicate whether objects or function calls will be sync or async.
You can use any of the provided flags, whichever makes most sense for your use case.

Examples:
    >>> 'sync' in VIABLE_FLAGS
    True

    >>> 'asynchronous' in VIABLE_FLAGS
    True

    >>> 'invalid' in VIABLE_FLAGS
    False
"""


def negate_if_necessary(flag: str, flag_value: bool) -> bool:
    """Negate the flag value if necessary based on the flag type.

    This function checks if the provided flag is in the set of affirmative or negative flags
    and negates the flag value accordingly. If the flag is not recognized, it raises an exception.

    Args:
        flag: The flag to check.
        flag_value: The value of the flag.

    Returns:
        The potentially negated flag value.

    Raises:
        exceptions.InvalidFlag: If the flag is not recognized.

    Examples:
        >>> negate_if_necessary('sync', True)
        True

        >>> negate_if_necessary('asynchronous', True)
        False

    See Also:
        - :func:`validate_flag_value`: Validates that the flag value is a boolean.
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

    This function ensures that the provided flag value is of type boolean. If not, it raises an exception.

    Args:
        flag: The flag being validated.
        flag_value: The value to validate.

    Returns:
        The validated flag value.

    Raises:
        exceptions.InvalidFlagValue: If the flag value is not a boolean.

    Examples:
        >>> validate_flag_value('sync', True)
        True

        >>> validate_flag_value('asynchronous', 'yes')
        Traceback (most recent call last):
        ...
        exceptions.InvalidFlagValue: Invalid flag value for 'asynchronous': 'yes'

    See Also:
        - :func:`negate_if_necessary`: Negates the flag value if necessary based on the flag type.
    """
    if not isinstance(flag_value, bool):
        raise exceptions.InvalidFlagValue(flag, flag_value)
    return flag_value
