
import functools
import logging

import async_property as ap  # type: ignore [import]

from a_sync import _helpers, config, exceptions
from a_sync._bound import ASyncBoundMethodAsyncDefault, ASyncMethodDescriptorAsyncDefault
from a_sync._descriptor import ASyncDescriptor
from a_sync._typing import *


logger = logging.getLogger(__name__)

class _ASyncPropertyDescriptorBase(ASyncDescriptor[T]):
    __wrapped__: AsyncPropertyGetter[T]
    __slots__ = "hidden_method_name", "hidden_method_descriptor", "_fget"
    def __init__(
        self, 
        _fget: AsyncPropertyGetter[T], 
        field_name: Optional[str] = None,
        **modifiers: config.ModifierKwargs,
    ) -> None:
        super().__init__(_fget, field_name, **modifiers)
        self.hidden_method_name = f"__{self.field_name}__"
        hidden_modifiers = dict(self.modifiers)
        hidden_modifiers["default"] = "async"
        self.hidden_method_descriptor: HiddenMethodDescriptor[T] =  HiddenMethodDescriptor(self.get, self.hidden_method_name, **hidden_modifiers)
        if asyncio.iscoroutinefunction(_fget):
            self._fget = self.__wrapped__
        else:
            self._fget = _helpers._asyncify(self.__wrapped__, self.modifiers.executor)
    async def get(self, instance: object) -> T:
        return await super().__get__(instance, None)
    def __get__(self, instance: Optional[object], owner: Any) -> T:
        if instance is None:
            return self
        awaitable = super().__get__(instance, owner)
        # if the user didn't specify a default behavior, we will defer to the instance
        if _is_a_sync_instance(instance):
            should_await = self.default == "sync" if self.default else instance.__a_sync_instance_should_await__
        else:
            should_await = self.default == "sync" if self.default else not asyncio.get_event_loop().is_running()  
        return _helpers._await(awaitable) if should_await else awaitable

class ASyncPropertyDescriptor(_ASyncPropertyDescriptorBase[T], ap.base.AsyncPropertyDescriptor):
    pass

class property(ASyncPropertyDescriptor[T]):...

class ASyncPropertyDescriptorSyncDefault(property[T]):
    """This is a helper class used for type checking. You will not run into any instance of this in prod."""

class ASyncPropertyDescriptorAsyncDefault(property[T]):
    """This is a helper class used for type checking. You will not run into any instance of this in prod."""
    def __get__(self, instance, owner: Any) -> Awaitable[T]:
        return super().__get__(instance, owner)


ASyncPropertyDecorator = Callable[[AsyncPropertyGetter[T]], property[T]]
ASyncPropertyDecoratorSyncDefault = Callable[[AsyncPropertyGetter[T]], ASyncPropertyDescriptorSyncDefault[T]]
ASyncPropertyDecoratorAsyncDefault = Callable[[AsyncPropertyGetter[T]], ASyncPropertyDescriptorAsyncDefault[T]]

@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorSyncDefault[T]:...

@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorSyncDefault[T]:...

@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorAsyncDefault[T]:...

@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecorator[T]:...
    
@overload
def a_sync_property(  # type: ignore [misc]
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorSyncDefault[T]:...
    
@overload
def a_sync_property(  # type: ignore [misc]
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorAsyncDefault[T]:...
    
@overload
def a_sync_property(  # type: ignore [misc]
    func: AnyPropertyGetter[T],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDescriptorSyncDefault[T]:...
    
@overload
def a_sync_property(  # type: ignore [misc]
    func: AnyPropertyGetter[T],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDescriptorAsyncDefault[T]:...
    
@overload
def a_sync_property(  # type: ignore [misc]
    func: AnyPropertyGetter[T],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDescriptor[T]:...
    
def a_sync_property(  # type: ignore [misc]
    func: Union[AnyPropertyGetter[T], DefaultMode] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> Union[
    ASyncPropertyDescriptor[T],
    ASyncPropertyDescriptorSyncDefault[T], 
    ASyncPropertyDescriptorAsyncDefault[T], 
    ASyncPropertyDecorator[T],
    ASyncPropertyDecoratorSyncDefault[T],
    ASyncPropertyDecoratorAsyncDefault[T],
]:
    func, modifiers = _parse_args(func, modifiers)
    if modifiers.get("default") == "sync":
        descriptor_class = ASyncPropertyDescriptorSyncDefault
    elif modifiers.get("default") == "async":
        descriptor_class = ASyncPropertyDescriptorAsyncDefault
    else:
        descriptor_class = property
    decorator = functools.partial(descriptor_class, **modifiers)
    return decorator if func is None else decorator(func)


class ASyncCachedPropertyDescriptor(_ASyncPropertyDescriptorBase[T], ap.cached.AsyncCachedPropertyDescriptor):
    __slots__ = "_fset", "_fdel", "__async_property__"
    def __init__(self, _fget, _fset=None, _fdel=None, field_name=None, **modifiers: Unpack[ModifierKwargs]):
        super().__init__(_fget, field_name, **modifiers)
        self._check_method_sync(_fset, 'setter')
        self._check_method_sync(_fdel, 'deleter')
        self._fset = _fset
        self._fdel = _fdel

class cached_property(ASyncCachedPropertyDescriptor[T]):...

class ASyncCachedPropertyDescriptorSyncDefault(cached_property[T]):
    """This is a helper class used for type checking. You will not run into any instance of this in prod."""

class ASyncCachedPropertyDescriptorAsyncDefault(cached_property[T]):
    """This is a helper class used for type checking. You will not run into any instance of this in prod."""

ASyncCachedPropertyDecorator = Callable[[AsyncPropertyGetter[T]], cached_property[T]]
ASyncCachedPropertyDecoratorSyncDefault = Callable[[AsyncPropertyGetter[T]], ASyncCachedPropertyDescriptorSyncDefault[T]]
ASyncCachedPropertyDecoratorAsyncDefault = Callable[[AsyncPropertyGetter[T]], ASyncCachedPropertyDescriptorAsyncDefault[T]]

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecoratorSyncDefault[T]:...

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecoratorAsyncDefault[T]:...

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None],
    default: DefaultMode,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecorator[T]:...

@overload
def a_sync_cached_property(  # type: ignore [misc]
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecoratorSyncDefault[T]:...

@overload
def a_sync_cached_property(  # type: ignore [misc]
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecoratorAsyncDefault[T]:...
    
@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: AnyPropertyGetter[T],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDescriptorSyncDefault[T]:... 

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: AnyPropertyGetter[T],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDescriptorAsyncDefault[T]:... 

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: AnyPropertyGetter[T],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDescriptor[T]:...
    
def a_sync_cached_property(  # type: ignore [misc]
    func: Optional[AnyPropertyGetter[T]] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> Union[
    ASyncCachedPropertyDescriptor[T],
    ASyncCachedPropertyDescriptorSyncDefault[T], 
    ASyncCachedPropertyDescriptorAsyncDefault[T], 
    ASyncCachedPropertyDecorator[T],
    ASyncCachedPropertyDecoratorSyncDefault[T],
    ASyncCachedPropertyDecoratorAsyncDefault[T],
]:
    func, modifiers = _parse_args(func, modifiers)
    if modifiers.get("default") == "sync":
        descriptor_class = ASyncCachedPropertyDescriptorSyncDefault
    elif modifiers.get("default") == "sync":
        descriptor_class = ASyncCachedPropertyDescriptorAsyncDefault
    else:
        descriptor_class = ASyncCachedPropertyDescriptor
    decorator = functools.partial(descriptor_class, **modifiers)
    return decorator if func is None else decorator(func)

class HiddenMethod(ASyncBoundMethodAsyncDefault[I, Tuple[()], T]):
    def __init__(self, instance: I, unbound: AnyFn[Concatenate[I, P], T], field_name: str, **modifiers: _helpers.ModifierKwargs) -> None:
        super().__init__(instance, unbound, **modifiers)
        self.__name__ = field_name
    def __repr__(self) -> str:
        instance_type = type(self.__self__)
        return f"<{self.__class__.__name__} for property {instance_type.__module__}.{instance_type.__name__}.{self.__name__[2:-2]} bound to {self.__self__}>"
    def _should_await(self, kwargs: dict) -> bool:
        try:
            return self.__self__.__a_sync_should_await_from_kwargs__(kwargs)
        except (AttributeError, exceptions.NoFlagsFound):
            return False
    def __await__(self) -> Generator[Any, None, T]:
        return self(sync=False).__await__()

class HiddenMethodDescriptor(ASyncMethodDescriptorAsyncDefault[I, Tuple[()], T]):
    def __get__(self, instance: I, owner: Any) -> HiddenMethod[I, T]:
        if instance is None:
            return self
        try:
            return instance.__dict__[self.field_name]
        except KeyError:
            bound = HiddenMethod(instance, self.__wrapped__, self.field_name, **self.modifiers)
            instance.__dict__[self.field_name] = bound
            logger.debug("new hidden method: %s", bound)
            return bound

def _is_a_sync_instance(instance: object) -> bool:
    try:
        return instance.__is_a_sync_instance__
    except AttributeError:
        from a_sync.abstract import ASyncABC
        is_a_sync = isinstance(instance, ASyncABC)
        instance.__is_a_sync_instance__ = is_a_sync
        return is_a_sync

def _parse_args(func: Union[None, DefaultMode, AsyncPropertyGetter[T]], modifiers: ModifierKwargs) -> Tuple[Optional[AsyncPropertyGetter[T]], ModifierKwargs]:
    if func in ['sync', 'async']:
        modifiers['default'] = func
        func = None
    return func, modifiers
