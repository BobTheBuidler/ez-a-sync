from a_sync._typing import *
from a_sync.modifiers.manager import ModifierManager, valid_modifiers


def get_modifiers_from(thing: Union[dict, type, object]) -> ModifierKwargs:
    if isinstance(thing, dict):
        return ModifierKwargs({modifier: thing[modifier] for modifier in valid_modifiers if modifier in thing})
    return ModifierKwargs({modifier: getattr(thing, modifier) for modifier in valid_modifiers if hasattr(thing, modifier)})