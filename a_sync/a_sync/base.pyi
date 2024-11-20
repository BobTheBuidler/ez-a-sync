from a_sync._typing import *
import functools
from _typeshed import Incomplete
from a_sync import exceptions as exceptions
from a_sync.a_sync.abstract import ASyncABC as ASyncABC
from a_sync.a_sync.flags import VIABLE_FLAGS as VIABLE_FLAGS

logger: Incomplete

class ASyncGenericBase(ASyncABC):
    """
    Base class for creating dual-function sync/async-capable classes without writing all your code twice.

    This class, via its inherited metaclass :class:`~ASyncMeta', provides the foundation for creating hybrid sync/async classes. It allows methods
    and properties to be defined once and used in both synchronous and asynchronous contexts.

    The class uses the :func:`a_sync` decorator internally to create dual-mode methods and properties.
    Subclasses should define their methods as coroutines (using `async def`) where possible, and
    use the `@a_sync.property` or `@a_sync.cached_property` decorators for properties that need to support both modes.

    Example:
        ```python
        class MyClass(ASyncGenericBase):
            def __init__(self, sync: bool):
                self.sync = sync

            @a_sync.property
            async def my_property(self):
                return await some_async_operation()

            @a_sync
            async def my_method(self):
                return await another_async_operation()

        # Synchronous usage
        obj = MyClass(sync=True)
        sync_result = obj.my_property
        sync_method_result = obj.my_method()

        # Asynchronous usage
        obj = MyClass(sync=False)
        async_result = await obj.my_property
        async_method_result = await obj.my_method()
        ```

    Note:
        When subclassing, be aware that all async methods and properties will be
        automatically wrapped to support both sync and async calls. This allows for
        seamless usage in different contexts without changing the underlying implementation.
    """

    def __init__(self) -> None: ...
    @functools.cached_property
    def __a_sync_flag_name__(self) -> str: ...
    @functools.cached_property
    def __a_sync_flag_value__(self) -> bool:
        """If you wish to be able to hotswap default modes, just duplicate this def as a non-cached property."""

    @classmethod
    def __a_sync_default_mode__(cls) -> bool: ...
