# cython: profile=False
# cython: linetrace=False

"""
This module provides functionality for handling synchronous and asynchronous flags
in the ez-a-sync library.

ez-a-sync uses 'flags' to indicate whether objects or function calls will be synchronous or asynchronous.

You can use any of the provided flags, whichever makes the most sense for your use case.

:obj:`AFFIRMATIVE_FLAGS`: Set of flags indicating synchronous behavior. Currently includes "sync".

:obj:`NEGATIVE_FLAGS`: Set of flags indicating asynchronous behavior. Currently includes "asynchronous".
"""

from a_sync import exceptions
from a_sync.a_sync.flags cimport AFFIRMATIVE_FLAGS, NEGATIVE_FLAGS


cdef object InvalidFlag = exceptions.InvalidFlag
cdef object InvalidFlagValue = exceptions.InvalidFlagValue
del exceptions


cdef inline bint negate_if_necessary(str flag, bint flag_value):
    """Negate the flag value if necessary based on the flag type.

    This function checks if the provided flag is in the set of affirmative or negative flags
    and negates the flag value accordingly. If the flag is not recognized, it raises an exception.

    Args:
        flag: The flag to check.
        flag_value: The value of the flag.

    Returns:
        The potentially negated flag value.

    Raises:
        TypeError: If the provided flag value is not of bint type.
        exceptions.InvalidFlag: If the flag is not recognized.

    Examples:
        >>> negate_if_necessary('sync', True)
        True

        >>> negate_if_necessary('asynchronous', True)
        False

    See Also:
        - :func:`validate_flag_value`: Validates that the flag value is a boolean.
    """
    if flag in AFFIRMATIVE_FLAGS:
        return flag_value
    elif flag in NEGATIVE_FLAGS:
        return not flag_value
    raise InvalidFlag(flag)


cdef inline bint validate_and_negate_if_necessary(str flag, object flag_value):
    try:
        return negate_if_necessary(flag, flag_value)
    except TypeError as e:
        raise InvalidFlagValue(flag, flag_value) from e.__cause__
