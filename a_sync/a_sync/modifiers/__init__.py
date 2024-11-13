from aiolimiter import AsyncLimiter

from a_sync._typing import *
from a_sync.primitives.locks import ThreadsafeSemaphore
from a_sync.a_sync.modifiers.manager import valid_modifiers


def get_modifiers_from(thing: Union[dict, type, object]) -> ModifierKwargs:
    """Extracts valid modifiers from a given object, type, or dictionary.

    Args:
        thing: The source from which to extract modifiers. It can be a dictionary,
            a type, or an object.

    Returns:
        A ModifierKwargs object containing the valid modifiers extracted from the input.
    """
    if isinstance(thing, dict):
        apply_class_defined_modifiers(thing)
        return ModifierKwargs({modifier: thing[modifier] for modifier in valid_modifiers if modifier in thing})  # type: ignore [misc]
    return ModifierKwargs({modifier: getattr(thing, modifier) for modifier in valid_modifiers if hasattr(thing, modifier)})  # type: ignore [misc]


def apply_class_defined_modifiers(attrs_from_metaclass: dict):
    """Applies class-defined modifiers to a dictionary of attributes.

    This function modifies the input dictionary in place. If the 'semaphore' key
    is present and its value is an integer, it is converted to a ThreadsafeSemaphore.
    If the 'runs_per_minute' key is present and its value is an integer, it is
    converted to an AsyncLimiter. If these keys are not present or their values
    are not integers, the function will silently do nothing.

    Args:
        attrs_from_metaclass: A dictionary of attributes from a metaclass.
    """
    if isinstance(val := attrs_from_metaclass.get("semaphore"), int):
        attrs_from_metaclass["semaphore"] = ThreadsafeSemaphore(val)
    if isinstance(val := attrs_from_metaclass.get("runs_per_minute"), int):
        attrs_from_metaclass["runs_per_minute"] = AsyncLimiter(val)