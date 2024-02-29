
import asyncio

import async_property as ap  # type: ignore [import]

from a_sync import config
from a_sync._typing import *
from a_sync.modified import ModifiedMixin
from a_sync.modifiers.manager import ModifierManager


class PropertyDescriptor(ModifiedMixin, Generic[T]):
    def __init__(self, _fget: Callable[..., T], field_name=None, **modifiers: ModifierKwargs):
        if not callable(_fget):
            raise ValueError(f'Unable to decorate {_fget}')
        self.modifiers = ModifierManager(modifiers)
        self._fn = _fget
        _fget = self.modifiers.apply_async_modifiers(_fget) if asyncio.iscoroutinefunction(_fget) else self._asyncify(_fget)
        super().__init__(_fget, field_name=field_name)  # type: ignore [call-arg]
    def __repr__(self) -> str:
        return f"<{self.__class__.__module__}.{self.__class__.__name__} for {self._fn} at {hex(id(self))}>"
    
class AsyncPropertyDescriptor(PropertyDescriptor[T], ap.base.AsyncPropertyDescriptor):
    pass
        
class AsyncCachedPropertyDescriptor(PropertyDescriptor[T], ap.cached.AsyncCachedPropertyDescriptor):
    __slots__ = "_fset", "_fdel", "__async_property__"
    def __init__(self, _fget, _fset=None, _fdel=None, field_name=None, **modifiers: Unpack[ModifierKwargs]):
        super().__init__(_fget, field_name, **modifiers)
        self._check_method_sync(_fset, 'setter')
        self._check_method_sync(_fdel, 'deleter')
        self._fset = _fset
        self._fdel = _fdel

class property(AsyncPropertyDescriptor[T]):...

class ASyncPropertyDescriptorSyncDefault(property[T]):
    """This is a helper class used for type checking. You will not run into any instance of this in prod."""

class ASyncPropertyDescriptorAsyncDefault(property[T]):
    """This is a helper class used for type checking. You will not run into any instance of this in prod."""
    def __get__(self, instance, owner) -> Awaitable[T]:
        return super().__get__(instance, owner)


ASyncPropertyDecorator = Callable[[Property[T]], property[T]]
ASyncPropertyDecoratorSyncDefault = Callable[[Property[T]], ASyncPropertyDescriptorSyncDefault[T]]
ASyncPropertyDecoratorAsyncDefault = Callable[[Property[T]], ASyncPropertyDescriptorAsyncDefault[T]]

@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorSyncDefault[T]:...


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
    return modifier_wrap if func is None else modifier_wrap(func)  # type: ignore [arg-type]
    

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
