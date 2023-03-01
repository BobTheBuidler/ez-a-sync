from aiolimiter import AsyncLimiter

from a_sync._typing import *
from a_sync.modifiers.manager import ModifierManager, valid_modifiers
from a_sync.semaphores import ThreadsafeSemaphore


def get_modifiers_from(thing: Union[dict, type, object]) -> ModifierKwargs:
    if isinstance(thing, dict):
        apply_class_defined_modifiers(thing)
        return ModifierKwargs({modifier: thing[modifier] for modifier in valid_modifiers if modifier in thing})  # type: ignore [misc]
    return ModifierKwargs({modifier: getattr(thing, modifier) for modifier in valid_modifiers if hasattr(thing, modifier)})  # type: ignore [misc]

def apply_class_defined_modifiers(attrs_from_metaclass: dict):
    if 'semaphore' in attrs_from_metaclass and isinstance(val := attrs_from_metaclass['semaphore'], int):
        attrs_from_metaclass['semaphore'] = ThreadsafeSemaphore(val)
    if "runs_per_minute" in attrs_from_metaclass and isinstance(val := attrs_from_metaclass['runs_per_minute'], int):
        attrs_from_metaclass['runs_per_minute'] = AsyncLimiter(val)
        