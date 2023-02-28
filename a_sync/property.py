
import asyncio
from typing import Callable, Literal, Optional, TypeVar, Union, overload

import async_property as ap
from a_sync import modifiers

T = TypeVar('T')

class AsyncPropertyDescriptor(ap.base.AsyncPropertyDescriptor):
    def __init__(self, _fget, field_name=None, **modifiers: modifiers.Modifiers):
        self.modifiers = modifiers
        super().__init__(_fget, field_name=field_name)
        
class AsyncCachedPropertyDescriptor(ap.cached.AsyncCachedPropertyDescriptor):
    def __init__(self, _fget, field_name=None, **modifiers: modifiers.Modifiers):
        self.modifiers = modifiers
        super().__init__(_fget, field_name=field_name)

@overload
def a_sync_property(
    func: Literal[None] = None,
    **modifiers: modifiers.Modifiers,
) -> Callable[[Callable[..., T]], AsyncPropertyDescriptor]:...
    
@overload
def a_sync_property(
    func: Callable[..., T] = None,
    **modifiers: modifiers.Modifiers,
) -> AsyncPropertyDescriptor:...
    
def a_sync_property(
    func: Optional[Callable[..., T]] = None,
    **modifiers: modifiers.Modifiers,
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
    **modifiers: modifiers.Modifiers,
) -> Callable[[Callable[..., T]], AsyncCachedPropertyDescriptor]:...
    
@overload
def a_sync_cached_property(
    func: Callable[..., T] = None,
    **modifiers: modifiers.Modifiers,
) -> AsyncCachedPropertyDescriptor:...
    
def a_sync_cached_property(
    func: Optional[Callable[..., T]] = None,
    **modifiers: modifiers.Modifiers,
) -> Union[
    AsyncCachedPropertyDescriptor,
    Callable[[Callable[..., T]], AsyncCachedPropertyDescriptor],
]:
    def modifier_wrap(func) -> AsyncCachedPropertyDescriptor:
        assert asyncio.iscoroutinefunction(func), 'Can only use with async def'
        return AsyncCachedPropertyDescriptor(func, **modifiers)
    return modifier_wrap if func is None else modifier_wrap(func)
