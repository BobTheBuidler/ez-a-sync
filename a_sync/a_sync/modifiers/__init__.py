"""
This file contains all logic for ez-a-sync's "modifiers".

Modifiers modify the behavior of ez-a-sync's ASync objects in various ways.

Submodules:
    cache: Handles caching mechanisms for async functions.
    limiter: Manages rate limiting for async functions.
    manager: Provides management of valid modifiers and their application.
    semaphores: Implements semaphore logic for controlling concurrency.

The modifiers available are:
- `cache_type`: Specifies the type of cache to use, such as 'memory'.
- `cache_typed`: Determines if types are considered for cache keys.
- `ram_cache_maxsize`: Sets the maximum size for the LRU cache.
- `ram_cache_ttl`: Defines the time-to-live for items in the cache.
- `runs_per_minute`: Sets a rate limit for function execution.
- `semaphore`: Specifies a semaphore for controlling concurrency.
- `executor`: Defines the executor for synchronous functions. This is not applied like the other modifiers but is used to manage the execution context for synchronous functions when they are called in an asynchronous manner.

See Also:
    - :mod:`a_sync.a_sync.modifiers.cache`
    - :mod:`a_sync.a_sync.modifiers.limiter`
    - :mod:`a_sync.a_sync.modifiers.manager`
    - :mod:`a_sync.a_sync.modifiers.semaphores`
"""

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

    Examples:
        Extracting modifiers from a class:

        >>> class Example:
        ...     cache_type = 'memory'
        ...     runs_per_minute = 60
        >>> get_modifiers_from(Example)
        ModifierKwargs({'cache_type': 'memory', 'runs_per_minute': 60})

        Extracting modifiers from a dictionary:

        >>> modifiers_dict = {'cache_type': 'memory', 'semaphore': 5}
        >>> get_modifiers_from(modifiers_dict)
        ModifierKwargs({'cache_type': 'memory', 'semaphore': ThreadsafeSemaphore(5)})

    See Also:
        - :class:`a_sync.a_sync.modifiers.manager.ModifierManager`
    """
    if isinstance(thing, dict):
        apply_class_defined_modifiers(thing)
        return ModifierKwargs((modifier, thing[modifier]) for modifier in valid_modifiers if modifier in thing)  # type: ignore [misc]
    return ModifierKwargs((modifier, getattr(thing, modifier)) for modifier in valid_modifiers if hasattr(thing, modifier))  # type: ignore [misc]


def apply_class_defined_modifiers(attrs_from_metaclass: dict):
    """Applies class-defined modifiers to a dictionary of attributes.

    This function modifies the input dictionary in place. If the 'semaphore' key
    is present and its value is an integer, it is converted to a ThreadsafeSemaphore.
    If the 'runs_per_minute' key is present and its value is an integer, it is
    converted to an AsyncLimiter. If these keys are not present or their values
    are not integers, the function will silently do nothing.

    Args:
        attrs_from_metaclass: A dictionary of attributes from a metaclass.

    Examples:
        Applying modifiers to a dictionary:

        >>> attrs = {'semaphore': 3, 'runs_per_minute': 60}
        >>> apply_class_defined_modifiers(attrs)
        >>> attrs['semaphore']
        ThreadsafeSemaphore(3)

        >>> attrs['runs_per_minute']
        AsyncLimiter(60)

    See Also:
        - :class:`a_sync.primitives.locks.ThreadsafeSemaphore`
        - :class:`aiolimiter.AsyncLimiter`
    """
    if isinstance(val := attrs_from_metaclass.get("semaphore"), int):
        attrs_from_metaclass["semaphore"] = ThreadsafeSemaphore(val)
    if isinstance(val := attrs_from_metaclass.get("runs_per_minute"), int):
        attrs_from_metaclass["runs_per_minute"] = AsyncLimiter(val)
