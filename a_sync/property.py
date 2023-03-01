
import asyncio

import async_property as ap

from a_sync._typing import *
from a_sync.modifiers import Modifiers

T = TypeVar('T')


class PropertyDescriptor(Modified[T]):
    def __init__(self, _fget, field_name=None, modifiers: Modifiers = Modifiers()):
        self.modifiers = modifiers
        super().__init__(_fget, field_name=field_name)
    
class AsyncPropertyDescriptor(PropertyDescriptor[T], ap.base.AsyncPropertyDescriptor):
    pass
        
class AsyncCachedPropertyDescriptor(PropertyDescriptor[T], ap.cached.AsyncCachedPropertyDescriptor):
    pass


@overload
def a_sync_property(
    func: Literal[None] = None,
    **modifiers: Modifiers,
) -> Callable[[Callable[..., T]], AsyncPropertyDescriptor]:...
    
@overload
def a_sync_property(
    func: Callable[..., T] = None,
    **modifiers: Modifiers,
) -> AsyncPropertyDescriptor:...
    
def a_sync_property(
    func: Optional[Callable[..., T]] = None,
    **modifiers: Modifiers,
) -> Union[
    AsyncPropertyDescriptor,
    Callable[[Callable[..., T]], AsyncPropertyDescriptor],
]:
    def modifier_wrap(func) -> AsyncPropertyDescriptor:
        assert asyncio.iscoroutinefunction(func), 'Can only use with async def'
        return AsyncPropertyDescriptor(func, **modifiers)
    return modifier_wrap if func is None else modifier_wrap(func)
    
@overload
def a_sync_cached_property(
    func: Literal[None] = None,
    **modifiers: Modifiers,
) -> Callable[[Callable[..., T]], AsyncCachedPropertyDescriptor]:...
    
@overload
def a_sync_cached_property(
    func: Callable[..., T] = None,
    **modifiers: Modifiers,
) -> AsyncCachedPropertyDescriptor:...
    
def a_sync_cached_property(
    func: Optional[Callable[..., T]] = None,
    **modifiers: Modifiers,
) -> Union[
    AsyncCachedPropertyDescriptor,
    Callable[[Callable[..., T]], AsyncCachedPropertyDescriptor],
]:
    def modifier_wrap(func) -> AsyncCachedPropertyDescriptor:
        assert asyncio.iscoroutinefunction(func), 'Can only use with async def'
        return AsyncCachedPropertyDescriptor(func, **modifiers)
    return modifier_wrap if func is None else modifier_wrap(func)
