from typing import Any, Set

AFFIRMATIVE_FLAGS: Set[str]
NEGATIVE_FLAGS: Set[str]
VIABLE_FLAGS: Set[str]

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
