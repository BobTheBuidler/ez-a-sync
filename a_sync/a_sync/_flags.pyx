"""
This module provides functionality for handling synchronous and asynchronous flags
in the ez-a-sync library.

ez-a-sync uses 'flags' to indicate whether objects or function calls will be synchronous or asynchronous.

You can use any of the provided flags, whichever makes the most sense for your use case.

:obj:`AFFIRMATIVE_FLAGS`: Set of flags indicating synchronous behavior. Currently includes "sync".

:obj:`NEGATIVE_FLAGS`: Set of flags indicating asynchronous behavior. Currently includes "asynchronous".

:obj:`VIABLE_FLAGS`: Set of all valid flags, combining both synchronous and asynchronous indicators.
"""

from typing import Any, Set

from a_sync import exceptions

AFFIRMATIVE_FLAGS: Set[str] = {"sync"}
"""Set of flags indicating synchronous behavior.

This set currently contains only the flag "sync", which is used to denote
synchronous operations within the ez-a-sync library.

Examples:
    >>> 'sync' in AFFIRMATIVE_FLAGS
    True

    >>> 'async' in AFFIRMATIVE_FLAGS
    False

See Also:
    :data:`NEGATIVE_FLAGS`: Flags indicating asynchronous behavior.
    :data:`VIABLE_FLAGS`: All valid flags, combining both sync and async indicators.
"""

NEGATIVE_FLAGS: Set[str] = {"asynchronous"}
"""Set of flags indicating asynchronous behavior.

This set currently contains only the flag "asynchronous", which is used to denote
asynchronous operations within the ez-a-sync library.

Examples:
    >>> 'asynchronous' in NEGATIVE_FLAGS
    True

    >>> 'sync' in NEGATIVE_FLAGS
    False

See Also:
    :data:`AFFIRMATIVE_FLAGS`: Flags indicating synchronous behavior.
    :data:`VIABLE_FLAGS`: All valid flags, combining both sync and async indicators.
"""

VIABLE_FLAGS: Set[str] = AFFIRMATIVE_FLAGS | NEGATIVE_FLAGS
"""Set of all valid flags, combining both synchronous and asynchronous indicators.

The ez-a-sync library uses these flags to indicate whether objects or function
calls will be synchronous or asynchronous. You can use any of the provided flags,
whichever makes the most sense for your use case.

Examples:
    >>> 'sync' in VIABLE_FLAGS
    True

    >>> 'asynchronous' in VIABLE_FLAGS
    True

    >>> 'invalid' in VIABLE_FLAGS
    False

See Also:
    :data:`AFFIRMATIVE_FLAGS`: Flags indicating synchronous behavior.
    :data:`NEGATIVE_FLAGS`: Flags indicating asynchronous behavior.
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
    return cnegate_if_necessary(flag, flag_value)


cdef bint cnegate_if_necessary(str flag, object flag_value):
    cdef bint value = validate_flag_value(flag, flag_value)
    if flag in AFFIRMATIVE_FLAGS:
        return value
    elif flag in NEGATIVE_FLAGS:
        return not value
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
