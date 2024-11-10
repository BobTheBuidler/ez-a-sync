"""
This module provides utility functions for handling keyword arguments related to synchronous and asynchronous flags.
"""

from typing import Optional

from a_sync import exceptions
from a_sync.a_sync import _flags


def get_flag_name(kwargs: dict) -> Optional[str]:
    """
    Get the name of the flag present in the kwargs.

    Args:
        kwargs: A dictionary of keyword arguments.

    Returns:
        The name of the flag if present, None otherwise.

    Raises:
        :class:`exceptions.TooManyFlags`: If more than one flag is present in the kwargs.
    """
    present_flags = [flag for flag in _flags.VIABLE_FLAGS if flag in kwargs]
    if len(present_flags) == 0:
        return None
    if len(present_flags) != 1:
        raise exceptions.TooManyFlags("kwargs", present_flags)
    return present_flags[0]


def is_sync(flag: str, kwargs: dict, pop_flag: bool = False) -> bool:
    """
    Determine if the operation should be synchronous based on the flag value.

    Args:
        flag: The name of the flag to check.
        kwargs: A dictionary of keyword arguments.
        pop_flag: Whether to remove the flag from kwargs. Defaults to False.

    Returns:
        True if the operation should be synchronous, False otherwise.
    """
    flag_value = kwargs.pop(flag) if pop_flag else kwargs[flag]
    return _flags.negate_if_necessary(flag, flag_value)
