# mypy: disable-error-code=valid-type
import functools

from a_sync._typing import *
from a_sync.config import user_set_default_modifiers, null_modifiers
from a_sync.modifiers import cache, limiter, semaphores

valid_modifiers = [key for key in ModifierKwargs.__annotations__ if not key.startswith('_') and not key.endswith('_')]

class ModifierManager(Dict[str, Any]):
    default: DefaultMode
    cache_type: CacheType
    cache_typed: bool
    ram_cache_maxsize: Optional[int]
    ram_cache_ttl: Optional[int]
    runs_per_minute: Optional[int]
    semaphore: SemaphoreSpec
    # sync modifiers
    executor: Executor

    def __init__(self, **modifiers: ModifierKwargs) -> None:
        for key in modifiers.keys():
            if key not in valid_modifiers:
                raise ValueError(f"'{key}' is not a supported modifier.")
        self._modifiers = modifiers
    def __repr__(self) -> str:
        return str(self._modifiers)
    def __getattribute__(self, modifier_key: str) -> Any:
        if modifier_key not in valid_modifiers:
            return super().__getattribute__(modifier_key)
        return self[modifier_key] if modifier_key in self else user_defaults[modifier_key]

    
    @property
    def use_limiter(self) -> bool:
        return self.runs_per_minute != nulls.runs_per_minute
    @property
    def use_semaphore(self) -> bool:
        return self.semaphore != nulls.semaphore
    @property
    def use_cache(self) -> bool:
        return any([
            self.cache_type != nulls.cache_type,
            self.ram_cache_maxsize != nulls.ram_cache_maxsize,
            self.ram_cache_ttl != nulls.ram_cache_ttl,
            self.cache_typed != nulls.cache_typed,
        ])
    
    def apply_async_modifiers(self, coro_fn: CoroFn[P, T]) -> CoroFn[P, T]:
        # NOTE: THESE STACK IN REVERSE ORDER
        if self.use_limiter:
            coro_fn = limiter.apply_rate_limit(coro_fn, self.runs_per_minute)
        if self.use_semaphore:
            coro_fn = semaphores.apply_semaphore(coro_fn, self.semaphore)
        if self.use_cache:
            coro_fn = cache.apply_async_cache(
                coro_fn,
                cache_type=self.cache_type or 'memory',
                cache_typed=self.cache_typed,
                ram_cache_maxsize=self.ram_cache_maxsize,
                ram_cache_ttl=self.ram_cache_ttl
            )
        return coro_fn
    
    def apply_sync_modifiers(self, function: SyncFn[P, T]) -> SyncFn[P, T]:
        @functools.wraps(function)
        def sync_modifier_wrap(*args: P.args, **kwargs: P.kwargs) -> T:
            return function(*args, **kwargs)
        # NOTE There are no sync modifiers at this time but they will be added here for my convenience.
        return sync_modifier_wrap
    
    # Dictionary api
    def items(self) -> List[Tuple[str, Any]]:
        return self._modifiers.items()
    def keys(self) -> List[str]:
        return self._modifiers.keys()
    def values(self) -> List[Any]:
        return self._modifiers.values()
    def __contains__(self, key: str) -> bool:
        return key in self._modifiers
    def __iter__(self) -> Iterator[str]:
        return self._modifiers.__iter__()
    def __len__(self) -> int:
        return len(self._modifiers)
    def __getitem__(self, modifier_key: str):
        return self._modifiers[modifier_key]  # type: ignore [literal-required]

nulls = ModifierManager(**null_modifiers)
user_defaults = ModifierManager(**user_set_default_modifiers)
