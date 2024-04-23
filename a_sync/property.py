
import functools
import logging

import async_property as ap  # type: ignore [import]

from a_sync import _helpers, config, decorator, exceptions
from a_sync._bound import ASyncBoundMethodAsyncDefault, ASyncMethodDescriptorAsyncDefault
from a_sync._descriptor import ASyncDescriptor
from a_sync._typing import *
from a_sync.modified import ASyncFunction, ASyncFunctionAsyncDefault, ASyncFunctionSyncDefault

if TYPE_CHECKING:
    from a_sync.task import TaskMapping


logger = logging.getLogger(__name__)

class _ASyncPropertyDescriptorBase(ASyncDescriptor[I, Tuple[()], T]):
    any: ASyncFunction[AnyIterable[I], bool]
    all: ASyncFunction[AnyIterable[I], bool]
    min: ASyncFunction[AnyIterable[I], T]
    max: ASyncFunction[AnyIterable[I], T]
    sum: ASyncFunction[AnyIterable[I], T]
    __wrapped__: Callable[[I], T]
    __slots__ = "hidden_method_name", "hidden_method_descriptor", "_fget"
    def __init__(
        self, 
        _fget: AsyncGetterFunction[I, T], 
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
    @overload
    def __get__(self, instance: None, owner: Any) -> Self:...
    @overload
    def __get__(self, instance: I, owner: Any) -> Awaitable[T]:...
    def __get__(self, instance: Optional[I], owner: Any) -> Union[Self, Awaitable[T]]:
        if instance is None:
            return self
        logger.debug("getting awaitable for %s for instance: %s owner: %s", self, instance, owner)
        awaitable = super().__get__(instance, owner)
        # if the user didn't specify a default behavior, we will defer to the instance
        if _is_a_sync_instance(instance):
            should_await = self.default == "sync" if self.default else instance.__a_sync_instance_should_await__
        else:
            should_await = self.default == "sync" if self.default else not asyncio.get_event_loop().is_running()  
        if should_await:
            logger.debug("awaiting awaitable for %s for instance: %s owner: %s", awaitable, self, instance, owner)
            retval = _helpers._await(awaitable)
        else:
            retval = awaitable
        logger.debug("returning %s for %s for instance: %s owner: %s", retval, self, instance, owner)
        return retval
    async def get(self, instance: I, owner: Any = None) -> T:
        if instance is None:
            raise ValueError(instance)
        logger.debug("awaiting %s for instance %s", self, instance)
        return await super().__get__(instance, owner)
    def map(self, instances: AnyIterable[I], owner: Any = None, concurrency: Optional[int] = None, name: str = "") -> "TaskMapping[I, T]":
        from a_sync.task import TaskMapping
        logger.debug("mapping %s to instances: %s owner: %s", self, instances, owner)
        return TaskMapping(self, instances, owner=owner, name=name or self.field_name, concurrency=concurrency)

class ASyncPropertyDescriptor(_ASyncPropertyDescriptorBase[I, T], ap.base.AsyncPropertyDescriptor):
    pass

class property(ASyncPropertyDescriptor[I, T]):...

class ASyncPropertyDescriptorSyncDefault(property[I, T]):
    default = "sync"
    any: ASyncFunctionSyncDefault[AnyIterable[I], bool]
    all: ASyncFunctionSyncDefault[AnyIterable[I], bool]
    min: ASyncFunctionSyncDefault[AnyIterable[I], T]
    max: ASyncFunctionSyncDefault[AnyIterable[I], T]
    sum: ASyncFunctionSyncDefault[AnyIterable[I], T]
    @overload
    def __get__(self, instance: None, owner: Any) -> Self:...
    @overload
    def __get__(self, instance: I, owner: Any) -> T:...
    def __get__(self, instance: Optional[I], owner: Any) -> Union[Self, T]:
        return _ASyncPropertyDescriptorBase.__get__(self, instance, owner)

class ASyncPropertyDescriptorAsyncDefault(property[I, T]):
    default = "async"
    any: ASyncFunctionAsyncDefault[AnyIterable[I], bool]
    all: ASyncFunctionAsyncDefault[AnyIterable[I], bool]
    min: ASyncFunctionAsyncDefault[AnyIterable[I], T]
    max: ASyncFunctionAsyncDefault[AnyIterable[I], T]
    sum: ASyncFunctionAsyncDefault[AnyIterable[I], T]


ASyncPropertyDecorator = Callable[[AnyGetterFunction[I, T]], property[I, T]]
ASyncPropertyDecoratorSyncDefault = Callable[[AnyGetterFunction[I, T]], ASyncPropertyDescriptorSyncDefault[I, T]]
ASyncPropertyDecoratorAsyncDefault = Callable[[AnyGetterFunction[I, T]], ASyncPropertyDescriptorAsyncDefault[I, T]]

@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecorator[I, T]:...

@overload
def a_sync_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDescriptor[I, T]:...

@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorSyncDefault[I, T]:...

@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorSyncDefault[I, T]:...

@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorAsyncDefault[I, T]:...

@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecorator[I, T]:...
    
@overload
def a_sync_property(  # type: ignore [misc]
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorSyncDefault[I, T]:...
    
@overload
def a_sync_property(  # type: ignore [misc]
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorAsyncDefault[I, T]:...
    
@overload
def a_sync_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDescriptorSyncDefault[I, T]:...
    
@overload
def a_sync_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDescriptorAsyncDefault[I, T]:...
    
@overload
def a_sync_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDescriptor[I, T]:...
    
def a_sync_property(  # type: ignore [misc]
    func: Union[AnyGetterFunction[I, T], DefaultMode] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> Union[
    ASyncPropertyDescriptor[I, T],
    ASyncPropertyDescriptorSyncDefault[I, T], 
    ASyncPropertyDescriptorAsyncDefault[I, T], 
    ASyncPropertyDecorator[I, T],
    ASyncPropertyDecoratorSyncDefault[I, T],
    ASyncPropertyDecoratorAsyncDefault[I, T],
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


class ASyncCachedPropertyDescriptor(_ASyncPropertyDescriptorBase[I, T], ap.cached.AsyncCachedPropertyDescriptor):
    __slots__ = "_fset", "_fdel", "__async_property__"
    def __init__(
        self, 
        _fget: AsyncGetterFunction[I, T], 
        _fset = None, 
        _fdel = None, 
        field_name=None, 
        **modifiers: Unpack[ModifierKwargs],
    ) -> None:
        super().__init__(_fget, field_name, **modifiers)
        self._check_method_sync(_fset, 'setter')
        self._check_method_sync(_fdel, 'deleter')
        self._fset = _fset
        self._fdel = _fdel

class cached_property(ASyncCachedPropertyDescriptor[I, T]):...

class ASyncCachedPropertyDescriptorSyncDefault(cached_property[I, T]):
    """This is a helper class used for type checking. You will not run into any instance of this in prod."""
    @overload
    def __get__(self, instance: None, owner: Any) -> Self:...
    @overload
    def __get__(self, instance: I, owner: Any) -> T:...
    def __get__(self, instance: Optional[I], owner: Any) -> Union[Self, T]:
        return _ASyncPropertyDescriptorBase.__get__(self, instance, owner)


class ASyncCachedPropertyDescriptorAsyncDefault(cached_property[I, T]):
    """This is a helper class used for type checking. You will not run into any instance of this in prod."""

ASyncCachedPropertyDecorator = Callable[[AnyGetterFunction[I, T]], cached_property[I, T]]
ASyncCachedPropertyDecoratorSyncDefault = Callable[[AnyGetterFunction[I, T]], ASyncCachedPropertyDescriptorSyncDefault[I, T]]
ASyncCachedPropertyDecoratorAsyncDefault = Callable[[AnyGetterFunction[I, T]], ASyncCachedPropertyDescriptorAsyncDefault[I, T]]

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecorator[I, T]:...

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDescriptor[I, T]:...

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecoratorSyncDefault[I, T]:...

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecoratorAsyncDefault[I, T]:...

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None],
    default: DefaultMode,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecorator[I, T]:...

@overload
def a_sync_cached_property(  # type: ignore [misc]
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecoratorSyncDefault[I, T]:...

@overload
def a_sync_cached_property(  # type: ignore [misc]
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecoratorAsyncDefault[I, T]:...
    
@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDescriptorSyncDefault[I, T]:... 

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDescriptorAsyncDefault[I, T]:... 

@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDescriptor[I, T]:...
    
def a_sync_cached_property(  # type: ignore [misc]
    func: Optional[AnyGetterFunction[I, T]] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> Union[
    ASyncCachedPropertyDescriptor[I, T],
    ASyncCachedPropertyDescriptorSyncDefault[I, T], 
    ASyncCachedPropertyDescriptorAsyncDefault[I, T], 
    ASyncCachedPropertyDecorator[I, T],
    ASyncCachedPropertyDecoratorSyncDefault[I, T],
    ASyncCachedPropertyDecoratorAsyncDefault[I, T],
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

def _parse_args(func: Union[None, DefaultMode, AsyncGetterFunction[I, T]], modifiers: ModifierKwargs) -> Tuple[Optional[AsyncGetterFunction[I, T]], ModifierKwargs]:
    if func in ['sync', 'async']:
        modifiers['default'] = func
        func = None
    return func, modifiers
