# mypy: disable-error-code=valid-type
import functools

from a_sync._typing import *
from a_sync.a_sync.config import user_set_default_modifiers, null_modifiers
from a_sync.a_sync.modifiers import cache, limiter, semaphores

valid_modifiers = [
    key
    for key in ModifierKwargs.__annotations__
    if not key.startswith("_") and not key.endswith("_")
]


class ModifierManager(Dict[str, Any]):
    """Manages modifiers for asynchronous and synchronous functions.

    This class is responsible for applying modifiers to functions, such as
    caching, rate limiting, and semaphores for asynchronous functions.
    """

    default: DefaultMode
    cache_type: CacheType
    cache_typed: bool
    ram_cache_maxsize: Optional[int]
    ram_cache_ttl: Optional[int]
    runs_per_minute: Optional[int]
    semaphore: SemaphoreSpec
    # sync modifiers
    executor: Executor
    """This is not applied like a typical modifier. The executor is used to run the sync function in an asynchronous context."""

    __slots__ = ("_modifiers",)

    def __init__(self, modifiers: ModifierKwargs) -> None:
        """Initializes the ModifierManager with the given modifiers.

        Args:
            modifiers: A dictionary of modifiers to be applied.

        Raises:
            ValueError: If an unsupported modifier is provided.
        """
        for key in modifiers.keys():
            if key not in valid_modifiers:
                raise ValueError(f"'{key}' is not a supported modifier.")
        self._modifiers = modifiers

    def __repr__(self) -> str:
        """Returns a string representation of the modifiers."""
        return str(self._modifiers)

    def __getattribute__(self, modifier_key: str) -> Any:
        """Gets the value of a modifier.

        Args:
            modifier_key: The key of the modifier to retrieve.

        Returns:
            The value of the modifier, or the default value if not set.
        """
        if modifier_key not in valid_modifiers:
            return super().__getattribute__(modifier_key)
        return (
            self[modifier_key] if modifier_key in self else user_defaults[modifier_key]
        )

    @property
    def use_limiter(self) -> bool:
        """Determines if a rate limiter should be used."""
        return self.runs_per_minute != nulls.runs_per_minute

    @property
    def use_semaphore(self) -> bool:
        """Determines if a semaphore should be used."""
        return self.semaphore != nulls.semaphore

    @property
    def use_cache(self) -> bool:
        """Determines if caching should be used."""
        return any(
            [
                self.cache_type != nulls.cache_type,
                self.ram_cache_maxsize != nulls.ram_cache_maxsize,
                self.ram_cache_ttl != nulls.ram_cache_ttl,
                self.cache_typed != nulls.cache_typed,
            ]
        )

    def apply_async_modifiers(self, coro_fn: CoroFn[P, T]) -> CoroFn[P, T]:
        """Applies asynchronous modifiers to a coroutine function.

        Args:
            coro_fn: The coroutine function to modify.

        Returns:
            The modified coroutine function.
        """
        # NOTE: THESE STACK IN REVERSE ORDER
        if self.use_limiter:
            coro_fn = limiter.apply_rate_limit(coro_fn, self.runs_per_minute)
        if self.use_semaphore:
            coro_fn = semaphores.apply_semaphore(coro_fn, self.semaphore)
        if self.use_cache:
            coro_fn = cache.apply_async_cache(
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
        """

        @functools.wraps(function)
        def sync_modifier_wrap(*args: P.args, **kwargs: P.kwargs) -> T:
            return function(*args, **kwargs)

        return sync_modifier_wrap

    # Dictionary api
    def keys(self) -> KeysView[str]:  # type: ignore [override]
        """Returns the keys of the modifiers."""
        return self._modifiers.keys()

    def values(self) -> ValuesView[Any]:  # type: ignore [override]
        """Returns the values of the modifiers."""
        return self._modifiers.values()

    def items(self) -> ItemsView[str, Any]:  # type: ignore [override]
        """Returns the items of the modifiers."""
        return self._modifiers.items()

    def __contains__(self, key: str) -> bool:  # type: ignore [override]
        """Checks if a key is in the modifiers."""
        return key in self._modifiers

    def __iter__(self) -> Iterator[str]:
        """Returns an iterator over the modifier keys."""
        return self._modifiers.__iter__()

    def __len__(self) -> int:
        """Returns the number of modifiers."""
        return len(self._modifiers)

    def __getitem__(self, modifier_key: str):
        """Gets the value of a modifier by key.

        Args:
            modifier_key: The key of the modifier to retrieve.

        Returns:
            The value of the modifier.
        """
        return self._modifiers[modifier_key]  # type: ignore [literal-required]


nulls = ModifierManager(null_modifiers)
user_defaults = ModifierManager(user_set_default_modifiers)
