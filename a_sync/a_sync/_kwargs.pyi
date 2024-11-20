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
    """
