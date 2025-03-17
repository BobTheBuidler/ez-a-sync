"""
This module enables developers to write both synchronous and asynchronous code without having to write redundant code.

The two main objects you should use are
    - a decorator `@a_sync()`
    - a base class `ASyncGenericBase` which can be used to create classes that can be utilized in both synchronous and asynchronous contexts.

The rest of the objects are exposed for type checking only, you should not make use of them otherwise.
"""

# TODO: double check on these before adding them to docs
# - two decorators @:class:`property` and @:class:`cached_property` for the creation of dual-function properties and cached properties, respectively.

from a_sync.a_sync.base import ASyncGenericBase
from a_sync.a_sync.decorator import a_sync
from a_sync.a_sync.function import (
    ASyncFunction,
    ASyncFunctionAsyncDefault,
    ASyncFunctionSyncDefault,
)
from a_sync.a_sync.modifiers.semaphores import apply_semaphore

# NOTE: Some of these we purposely import without including in __all__. Do not remove.
from a_sync.a_sync.property import (
    ASyncCachedPropertyDescriptor,
    ASyncCachedPropertyDescriptorAsyncDefault,
    ASyncCachedPropertyDescriptorSyncDefault,
    ASyncPropertyDescriptor,
    ASyncPropertyDescriptorAsyncDefault,
    ASyncPropertyDescriptorSyncDefault,
    HiddenMethod,
    HiddenMethodDescriptor,
)
from a_sync.a_sync.property import ASyncCachedPropertyDescriptor as cached_property
from a_sync.a_sync.property import ASyncPropertyDescriptor as property
from a_sync.a_sync.singleton import ASyncGenericSingleton


__all__ = [
    # entrypoints
    "a_sync",
    "ASyncGenericBase",
    # maybe entrypoints (?)
    # TODO: double check how I intended for these to be used
    "property",
    "cached_property",
    # classes exposed for type hinting only
    "ASyncFunction",
    "ASyncPropertyDescriptor",
    "ASyncCachedPropertyDescriptor",
    "HiddenMethod",
    "HiddenMethodDescriptor",
]
