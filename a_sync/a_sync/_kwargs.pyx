"""
This module provides utility functions for handling keyword arguments related to synchronous and asynchronous flags.
"""

from typing import Optional
from libc.stdint cimport uint8_t

from a_sync import exceptions
from a_sync.a_sync._flags import VIABLE_FLAGS
from a_sync.a_sync._flags cimport cnegate_if_necessary


def get_flag_name(kwargs: dict) -> Optional[str]:
    """
    Get the name of the flag present in the kwargs.

    Args:
        kwargs: A dictionary of keyword arguments.

    Returns:
        The name of the flag if present, None otherwise.

    Raises:
        :class:`exceptions.TooManyFlags`: If more than one flag is present in the kwargs,
        the exception includes the message "kwargs" and the list of present flags.

    Examples:
        >>> get_flag_name({'sync': True})
        'sync'

        >>> get_flag_name({'asynchronous': False})
        'asynchronous'

        >>> get_flag_name({})
        None

    See Also:
        :func:`is_sync`: Determines if the operation should be synchronous based on the flag value.
    """
    cdef list present_flags = [flag for flag in VIABLE_FLAGS if flag in kwargs]
    cdef uint8_t flags_count = len(present_flags)
    if flags_count == 0:
        return None
    if flags_count != 1:
        raise exceptions.TooManyFlags("kwargs", present_flags)
    return present_flags[0]


def is_sync(flag: str, kwargs: dict, pop_flag: bool = False) -> bool:
    """
    Determine if the operation should be synchronous based on the flag value.

    Args:
        flag (str): The name of the flag to check.
        kwargs (dict): A dictionary of keyword arguments.
        pop_flag (bool, optional): Whether to remove the flag from kwargs. Defaults to False.

    Examples:
        >>> is_sync('sync', {'sync': True})
        True

        >>> is_sync('asynchronous', {'asynchronous': False})
        False

        >>> is_sync('sync', {'sync': True}, pop_flag=True)
        True

    See Also:
        :func:`get_flag_name`: Retrieves the name of the flag present in the kwargs.
    """
    return is_sync_c(flag, kwargs, pop_flag)

cdef bint is_sync_c(str flag, dict kwargs, bint pop_flag):
    if pop_flag:
        return cnegate_if_necessary(flag, kwargs.pop(flag))
    else:
        return cnegate_if_necessary(flag, kwargs[flag])