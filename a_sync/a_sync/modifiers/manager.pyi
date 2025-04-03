from a_sync._typing import *
from _typeshed import Incomplete
from a_sync.a_sync.config import (
    null_modifiers as null_modifiers,
    user_set_default_modifiers as user_set_default_modifiers,
)
from a_sync.a_sync.modifiers import (
    cache as cache,
    limiter as limiter,
    semaphores as semaphores,
)
from typing import Any

valid_modifiers: Tuple[str, ...]

class ModifierManager(Dict[str, Any]):
    """Manages modifiers for asynchronous and synchronous functions.

    This class is responsible for applying modifiers to functions, such as
    caching, rate limiting, and semaphores for asynchronous functions. It also
    handles synchronous functions, although no sync modifiers are currently
    implemented.

    Examples:
        Creating a ModifierManager with specific modifiers:

        >>> modifiers = ModifierKwargs(cache_type='memory', runs_per_minute=60)
        >>> manager = ModifierManager(modifiers)

        Applying modifiers to an asynchronous function:

        >>> async def my_coro():
        ...     pass
        >>> modified_coro = manager.apply_async_modifiers(my_coro)

        Applying modifiers to a synchronous function (no sync modifiers applied):

        >>> def my_function():
        ...     pass
        >>> modified_function = manager.apply_sync_modifiers(my_function)

    See Also:
        - :class:`a_sync.a_sync.modifiers.cache`
        - :class:`a_sync.a_sync.modifiers.limiter`
        - :class:`a_sync.a_sync.modifiers.semaphores`
    """

    default: DefaultMode
    cache_type: CacheType
    cache_typed: bool
    ram_cache_maxsize: Optional[int]
    ram_cache_ttl: Optional[int]
    runs_per_minute: Optional[int]
    semaphore: SemaphoreSpec
    executor: Executor
    def __init__(self, modifiers: ModifierKwargs) -> None:
        """Initializes the ModifierManager with the given modifiers.

        Args:
            modifiers: A dictionary of modifiers to be applied.

        Raises:
            ValueError: If an unsupported modifier is provided.
        """

    def __getattribute__(self, modifier_key: str) -> Any:
        """Gets the value of a modifier.

        Args:
            modifier_key: The key of the modifier to retrieve.

        Returns:
            The value of the modifier, or the default value if not set.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> manager.cache_type
            'memory'
        """

    @property
    def use_limiter(self) -> bool:
        """Determines if a rate limiter should be used.

        Examples:
            >>> manager = ModifierManager(runs_per_minute=60)
            >>> manager.use_limiter
            True
        """

    @property
    def use_semaphore(self) -> bool:
        """Determines if a semaphore should be used.

        Examples:
            >>> manager = ModifierManager(semaphore=Semaphore(5))
            >>> manager.use_semaphore
            True
        """

    @property
    def use_cache(self) -> bool:
        """Determines if caching should be used.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> manager.use_cache
            True
        """

    def apply_async_modifiers(self, coro_fn: CoroFn[P, T]) -> CoroFn[P, T]:
        """Applies asynchronous modifiers to a coroutine function.

        Args:
            coro_fn: The coroutine function to modify.

        Returns:
            The modified coroutine function.

        Examples:
            >>> async def my_coro():
            ...     pass
            >>> manager = ModifierManager(runs_per_minute=60)
            >>> modified_coro = manager.apply_async_modifiers(my_coro)
        """

    def apply_sync_modifiers(self, function: SyncFn[P, T]) -> SyncFn[P, T]:
        """Wraps a synchronous function.

        Note:
            There are no sync modifiers at this time, but they will be added here for convenience.

        Args:
            function: The synchronous function to wrap.

        Returns:
            The wrapped synchronous function.

        Examples:
            >>> def my_function():
            ...     pass
            >>> manager = ModifierManager()
            >>> modified_function = manager.apply_sync_modifiers(my_function)
        """

    def keys(self) -> KeysView[str]:
        """Returns the keys of the modifiers.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> list(manager.keys())
            ['cache_type']
        """

    def values(self) -> ValuesView[Any]:
        """Returns the values of the modifiers.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> list(manager.values())
            ['memory']
        """

    def items(self) -> ItemsView[str, Any]:
        """Returns the items of the modifiers.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> list(manager.items())
            [('cache_type', 'memory')]
        """

    def __contains__(self, key: str) -> bool:
        """Checks if a key is in the modifiers.

        Args:
            key: The key to check.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> 'cache_type' in manager
            True
        """

    def __iter__(self) -> Iterator[str]:
        """Returns an iterator over the modifier keys.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> list(iter(manager))
            ['cache_type']
        """

    def __len__(self) -> int:
        """Returns the number of modifiers.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> len(manager)
            1
        """

    def __getitem__(self, modifier_key: str):
        """Gets the value of a modifier by key.

        Args:
            modifier_key: The key of the modifier to retrieve.

        Returns:
            The value of the modifier.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> manager['cache_type']
            'memory'
        """

NULLS: Incomplete
USER_DEFAULTS: Incomplete
