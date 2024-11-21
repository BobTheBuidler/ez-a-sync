"""
This module provides utility functions for handling keyword arguments related to synchronous and asynchronous flags.
"""

from libc.stdint cimport uint8_t

from a_sync import exceptions
from a_sync.a_sync._flags cimport negate_if_necessary
from a_sync.a_sync.flags import VIABLE_FLAGS


cdef str get_flag_name(dict kwargs):
    """
    Get the name of the flag present in the kwargs.

    Args:
        kwargs: A dictionary of keyword arguments.

    Returns:
        The name of the flag if present, an empty string otherwise.

    Raises:
        :class:`exceptions.TooManyFlags`: If more than one flag is present in the kwargs,
        the exception includes the message "kwargs" and the list of present flags.

    Examples:
        >>> get_flag_name({'sync': True})
        'sync'

        >>> get_flag_name({'asynchronous': False})
        'asynchronous'

        >>> get_flag_name({})
        ''
    """
    cdef list present_flags = [flag for flag in VIABLE_FLAGS if flag in kwargs]
    cdef uint8_t flags_count = len(present_flags)
    if flags_count == 0:
        return ""  # indicates no flag is present
    elif flags_count == 1:
        return present_flags[0]
    raise exceptions.TooManyFlags("kwargs", present_flags)


cdef bint is_sync(str flag, dict kwargs, bint pop_flag):
    """
    Determine if the operation should be synchronous based on the flag value.

    Args:
        flag (str): The name of the flag to check.
        kwargs (dict): A dictionary of keyword arguments.
        pop_flag (bool, optional): Whether to remove the flag from kwargs. Defaults to False.

    See Also:
        :func:`get_flag_name`: Retrieves the name of the flag present in the kwargs.
    """
    if pop_flag:
        # NOTE: we should techincally raise InvalidFlagValue here but I dont want to set flag_value to a var
        return negate_if_necessary(flag, kwargs.pop(flag))
    else:
        try:
            return negate_if_necessary(flag, kwargs[flag])
        except TypeError as e:
            raise exceptions.InvalidFlagValue(flag, kwargs[flag]) from e.__cause__