# mypy: disable-error-code=valid-type
import typing
from libc.stdint cimport uint8_t

from a_sync._typing import CoroFn, ModifierKwargs, P, SyncFn, T
from a_sync.a_sync.config import user_set_default_modifiers, null_modifiers
from a_sync.a_sync.modifiers import cache, limiter, semaphores
from a_sync.functools cimport wraps


# cdef typing
cdef object Any = typing.Any
cdef object Iterator = typing.Iterator
del typing

# cdef modifier decorators
cdef object apply_async_cache = cache.apply_async_cache
cdef object apply_rate_limit = limiter.apply_rate_limit
cdef object apply_semaphore = semaphores.apply_semaphore
del cache, limiter, semaphores


# TODO give me a docstring
valid_modifiers = tuple(
    key
    for key in ModifierKwargs.__annotations__
    if not key.startswith("_") and not key.endswith("_")
)

cdef tuple[str, ...] _valid_modifiers = valid_modifiers

cdef object _getattribute = object.__getattribute__

cdef class ModifierManager:
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
    def __cinit__(self, dict[str, object] modifiers, bint _skip_check = False) -> None:
        """Initializes the ModifierManager with the given modifiers.

        Args:
            modifiers: A dictionary of modifiers to be applied.

        Raises:
            ValueError: If an unsupported modifier is provided.
        """
        cdef str key
        if not _skip_check:
            for key in modifiers.keys():
                if key not in _valid_modifiers:
                    raise ValueError(f"'{key}' is not a supported modifier.")
        self._modifiers = modifiers

    def __repr__(self) -> str:
        """Returns a string representation of the modifiers."""
        return str(self._modifiers)

    def __getattribute__(self, str modifier_key) -> Any:
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
        if modifier_key not in _valid_modifiers:
            return _getattribute(self, modifier_key)
        return (
            self._modifiers[modifier_key]
            if modifier_key in self._modifiers
            else USER_DEFAULTS._modifiers[modifier_key]
        )

    @property
    def use_limiter(self) -> bint:
        """Determines if a rate limiter should be used.

        Examples:
            >>> manager = ModifierManager(runs_per_minute=60)
            >>> manager.use_limiter
            True
        """
        return self.runs_per_minute != NULLS.runs_per_minute

    @property
    def use_semaphore(self) -> bint:
        """Determines if a semaphore should be used.

        Examples:
            >>> manager = ModifierManager(semaphore=SemaphoreSpec())
            >>> manager.use_semaphore
            True
        """
        return self.semaphore != NULLS.semaphore

    @property
    def use_cache(self) -> bint:
        """Determines if caching should be used.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> manager.use_cache
            True
        """
        return any(
            [
                self.cache_type != NULLS.cache_type,
                self.ram_cache_maxsize != NULLS.ram_cache_maxsize,
                self.ram_cache_ttl != NULLS.ram_cache_ttl,
                self.cache_typed != NULLS.cache_typed,
            ]
        )

    cpdef object apply_async_modifiers(self, coro_fn: CoroFn[P, T]):
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
        # NOTE: THESE STACK IN REVERSE ORDER
        if self.use_limiter:
            coro_fn = apply_rate_limit(coro_fn, self.runs_per_minute)
        if self.use_semaphore:
            coro_fn = apply_semaphore(coro_fn, self.semaphore)
        if self.use_cache:
            coro_fn = apply_async_cache(
                coro_fn,
                cache_type=self.cache_type or "memory",
                cache_typed=self.cache_typed,
                ram_cache_maxsize=self.ram_cache_maxsize,
                ram_cache_ttl=self.ram_cache_ttl,
            )
        return coro_fn

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

        @wraps(function)
        def sync_modifier_wrap(*args: P.args, **kwargs: P.kwargs) -> T:
            return function(*args, **kwargs)

        return sync_modifier_wrap

    # Dictionary-like API
    def keys(self) -> KeysView[str]:  # type: ignore [override]
        """Returns the keys of the modifiers.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> list(manager.keys())
            ['cache_type']
        """
        return self._modifiers.keys()

    def values(self) -> ValuesView[Any]:  # type: ignore [override]
        """Returns the values of the modifiers.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> list(manager.values())
            ['memory']
        """
        return self._modifiers.values()

    def items(self) -> ItemsView[str, Any]:  # type: ignore [override]
        """Returns the items of the modifiers.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> list(manager.items())
            [('cache_type', 'memory')]
        """
        return self._modifiers.items()

    def __contains__(self, str key) -> bint:  # type: ignore [override]
        """Checks if a key is in the modifiers.

        Args:
            key: The key to check.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> 'cache_type' in manager
            True
        """
        return key in self._modifiers

    def __iter__(self) -> Iterator[str]:
        """Returns an iterator over the modifier keys.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> list(iter(manager))
            ['cache_type']
        """
        return self._modifiers.__iter__()

    def __len__(self) -> uint8_t:
        """Returns the number of modifiers.

        Examples:
            >>> manager = ModifierManager(cache_type='memory')
            >>> len(manager)
            1
        """
        return len(<dict>self._modifiers)

    def __getitem__(self, str modifier_key) -> Any:
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
        return self._modifiers[modifier_key]  # type: ignore [literal-required]


# TODO give us docstrings
cdef public ModifierManager NULLS, USER_DEFAULTS
NULLS = ModifierManager(null_modifiers)
USER_DEFAULTS = ModifierManager(user_set_default_modifiers)
