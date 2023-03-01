
import asyncio

import async_property as ap

from a_sync import config
from a_sync._typing import *
from a_sync.modified import Modified
from a_sync.modifiers import ModifierManager


class PropertyDescriptor(Modified[T]):
    def __init__(self, _fget, field_name=None, modifiers: ModifierManager = ModifierManager()):
        self.modifiers = modifiers
        super().__init__(_fget, field_name=field_name)
    
class AsyncPropertyDescriptor(PropertyDescriptor[T], ap.base.AsyncPropertyDescriptor):
    pass
        
class AsyncCachedPropertyDescriptor(PropertyDescriptor[T], ap.cached.AsyncCachedPropertyDescriptor):
    pass

@overload
def a_sync_property(
    func: Literal[None] = None,
    default: Literal['sync', 'async', None] = config.DEFAULT_MODE,
    **modifiers: ModifierKwargs,
) -> Callable[[Callable[..., T]], AsyncPropertyDescriptor[T]]:...
    
@overload
def a_sync_property(
    func: Callable[..., T] = None,
    default: Literal['sync', 'async', None] = config.DEFAULT_MODE,
    **modifiers: ModifierKwargs,
) -> AsyncPropertyDescriptor[T]:...
    
def a_sync_property(
    func: Optional[Callable[..., T]] = None,
    default: Literal['sync', 'async', None] = config.DEFAULT_MODE,
    **modifiers: ModifierKwargs,
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
def a_sync_cached_property(
    func: Literal[None] = None,
    default: Literal['sync', 'async', None] = config.DEFAULT_MODE,
    **modifiers: ModifierKwargs,
) -> Callable[[Callable[..., T]], AsyncCachedPropertyDescriptor[T]]:...
    
@overload
def a_sync_cached_property(
    func: Callable[..., T] = None,
    default: Literal['sync', 'async', None] = config.DEFAULT_MODE,
    **modifiers: ModifierKwargs,
) -> AsyncCachedPropertyDescriptor[T]:...
    
def a_sync_cached_property(
    func: Optional[Callable[..., T]] = None,
    **modifiers: ModifierKwargs,
) -> Union[
    AsyncCachedPropertyDescriptor[T],
    Callable[[Callable[..., T]], AsyncCachedPropertyDescriptor[T]],
]:
    def modifier_wrap(func) -> AsyncCachedPropertyDescriptor[T]:
        assert asyncio.iscoroutinefunction(func), 'Can only use with async def'
        return AsyncCachedPropertyDescriptor(func, modifiers=ModifierManager(modifiers))
    return modifier_wrap if func is None else modifier_wrap(func)
