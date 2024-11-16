from typing import Optional

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
        >>> get_flag_name({\'sync\': True})
        \'sync\'

        >>> get_flag_name({\'asynchronous\': False})
        \'asynchronous\'

        >>> get_flag_name({})
        None

    See Also:
        :func:`is_sync`: Determines if the operation should be synchronous based on the flag value.
    """

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
