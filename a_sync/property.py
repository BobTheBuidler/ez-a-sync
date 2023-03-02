
import asyncio

import async_property as ap  # type: ignore [import]

from a_sync import config
from a_sync._typing import *
from a_sync.modified import Modified
from a_sync.modifiers import ModifierManager


class PropertyDescriptor(Modified[T]):
    def __init__(self, _fget: Callable[..., T], field_name=None, **modifiers: ModifierKwargs):
        if not callable(_fget):
            raise ValueError(f'Unable to decorate {_fget}')
        self.modifiers = ModifierManager(**modifiers)
        _fget = self.modifiers.apply_async_modifiers(_fget) if asyncio.iscoroutinefunction(_fget) else self._asyncify(_fget)
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
) -> Callable[[Property[T]], AsyncPropertyDescriptor[T]]:...
    
@overload
def a_sync_property(  # type: ignore [misc]
    func: Property[T],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> AsyncPropertyDescriptor[T]:...
    
def a_sync_property(  # type: ignore [misc]
    func: Union[Property[T], DefaultMode] = None,
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> Union[
    AsyncPropertyDescriptor[T],
    Callable[[Property[T]], AsyncPropertyDescriptor[T]],
]:
    if func in ['sync', 'async']:
        modifiers['default'] = func
        func = None
    def modifier_wrap(func: Property[T]) -> AsyncPropertyDescriptor[T]:
        return AsyncPropertyDescriptor(func, **modifiers)
    return modifier_wrap if func is None else modifier_wrap(func)
    

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None],
    default: DefaultMode,
    **modifiers: Unpack[ModifierKwargs],
) -> Callable[[Property[T]], AsyncCachedPropertyDescriptor[T]]:...
    
@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Property[T],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> AsyncCachedPropertyDescriptor[T]:...
    
def a_sync_cached_property(  # type: ignore [misc]
    func: Optional[Property[T]] = None,
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> Union[
    AsyncCachedPropertyDescriptor[T],
    Callable[[Property[T]], AsyncCachedPropertyDescriptor[T]],
]:
    def modifier_wrap(func: Property[T]) -> AsyncCachedPropertyDescriptor[T]:
        return AsyncCachedPropertyDescriptor(func, **modifiers)
    return modifier_wrap if func is None else modifier_wrap(func)
