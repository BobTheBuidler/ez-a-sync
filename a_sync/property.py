
import asyncio

import async_property as ap  # type: ignore [import]

from a_sync import config
from a_sync._typing import *
from a_sync.modified import Modified
from a_sync.modifiers import ModifierManager


class PropertyDescriptor(Modified[T]):
    def __init__(self, _fget, field_name=None, modifiers: ModifierManager = ModifierManager()):
        self.modifiers = modifiers
        super().__init__(_fget, field_name=field_name)  # type: ignore [call-arg]
    
class AsyncPropertyDescriptor(PropertyDescriptor[T], ap.base.AsyncPropertyDescriptor):
    pass
        
class AsyncCachedPropertyDescriptor(PropertyDescriptor[T], ap.cached.AsyncCachedPropertyDescriptor):
    pass

@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> Callable[[Callable[..., T]], AsyncPropertyDescriptor[T]]:...
    
@overload
def a_sync_property(  # type: ignore [misc]
    func: Callable[..., T],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> AsyncPropertyDescriptor[T]:...
    
def a_sync_property(  # type: ignore [misc]
    func: Union[Callable[..., T], DefaultMode] = None,
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> Union[
    AsyncPropertyDescriptor[T],
    Callable[[Callable[..., T]], AsyncPropertyDescriptor[T]],
]:
    if func in ['sync', 'async']:
        modifiers['default'] = func
        func = None
    def modifier_wrap(func) -> AsyncPropertyDescriptor[T]:
        assert asyncio.iscoroutinefunction(func), func #'Can only use with async def'
        return AsyncPropertyDescriptor(func, modifiers=ModifierManager(modifiers))
    return modifier_wrap if func is None else modifier_wrap(func)
    
@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None],
    default: DefaultMode,
    **modifiers: Unpack[ModifierKwargs],
) -> Callable[[Callable[..., T]], AsyncCachedPropertyDescriptor[T]]:...
    
@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Callable[..., T],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> AsyncCachedPropertyDescriptor[T]:...
    
def a_sync_cached_property(  # type: ignore [misc]
    func: Optional[Callable[..., T]] = None,
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> Union[
    AsyncCachedPropertyDescriptor[T],
    Callable[[Callable[..., T]], AsyncCachedPropertyDescriptor[T]],
]:
    def modifier_wrap(func) -> AsyncCachedPropertyDescriptor[T]:
        assert asyncio.iscoroutinefunction(func), 'Can only use with async def'
        return AsyncCachedPropertyDescriptor(func, modifiers=ModifierManager(modifiers))
    return modifier_wrap if func is None else modifier_wrap(func)
