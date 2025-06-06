import asyncio
import functools
import typing
from copy import copy as _copy
from logging import getLogger
from typing import Any, Awaitable, Callable, Generator, Optional, Tuple, Type, Union

import async_property as ap  # type: ignore [import]
from typing_extensions import Concatenate, Self, Unpack

from a_sync._smart cimport shield
from a_sync._typing import (AnyFn, AnyGetterFunction, AnyIterable, AsyncGetterFunction, 
                            DefaultMode, I, ModifierKwargs, P, T)
from a_sync.a_sync import _descriptor, config, function, method
from a_sync.a_sync._helpers cimport _asyncify, _await

from a_sync.a_sync.function cimport _ModifiedMixin
from a_sync.a_sync.method cimport _ASyncBoundMethod, _is_a_sync_instance, _update_cache_timer
from a_sync.async_property import cached
from a_sync.async_property.cached cimport AsyncCachedPropertyInstanceState
from a_sync.asyncio.create_task cimport ccreate_task_simple
from a_sync.functools cimport wraps

if typing.TYPE_CHECKING:
    from a_sync.task import TaskMapping

else:
    # to prevent circ import issues we will import this later
    TaskMapping = None


# cdef asyncio
cdef object get_event_loop = asyncio.get_event_loop
cdef object iscoroutinefunction = asyncio.iscoroutinefunction
cdef object Lock = asyncio.Lock
cdef object Task = asyncio.Task
del asyncio

# cdef copy
cdef object copy = _copy
del _copy

# cdef functools
cdef object partial = functools.partial
del functools

# cdef logging
cdef public object logger = getLogger(__name__)
cdef object _logger_is_enabled = logger.isEnabledFor
cdef object _logger_debug = logger.debug
cdef object _logger_log = logger._log
cdef object DEBUG = 10
del getLogger

# cdef typing
cdef object Literal = typing.Literal
cdef object overload = typing.overload
del typing


# cdef a_sync.a_sync._descriptor
cdef object ASyncDescriptor = _descriptor.ASyncDescriptor
del _descriptor

# cdef a_sync.a_sync.function
cdef object ASyncFunction = function.ASyncFunction
cdef object ASyncFunctionAsyncDefault = function.ASyncFunctionAsyncDefault
cdef object ASyncFunctionSyncDefault = function.ASyncFunctionSyncDefault
del function

# cdef a_sync.a_sync.method
cdef object ASyncBoundMethod = method.ASyncBoundMethod
cdef object ASyncBoundMethodAsyncDefault = method.ASyncBoundMethodAsyncDefault
cdef object ASyncMethodDescriptorAsyncDefault = method.ASyncMethodDescriptorAsyncDefault
del method


class _ASyncPropertyDescriptorBase(ASyncDescriptor[I, Tuple[()], T]):
    """Base class for creating asynchronous properties.

    This class provides the foundation for defining properties that can be accessed
    both synchronously and asynchronously. It includes utility methods for common
    operations such as `any`, `all`, `min`, `max`, and `sum`.
    """

    any: ASyncFunction[AnyIterable[I], bool]
    """An ASyncFunction that checks if any result is truthy."""

    all: ASyncFunction[AnyIterable[I], bool]
    """An ASyncFunction that checks if all results are truthy."""

    min: ASyncFunction[AnyIterable[I], T]
    """An ASyncFunction that returns the minimum result."""

    max: ASyncFunction[AnyIterable[I], T]
    """An ASyncFunction that returns the maximum result."""

    sum: ASyncFunction[AnyIterable[I], T]
    """An ASyncFunction that returns the sum of results."""

    hidden_method_descriptor: "HiddenMethodDescriptor[T]"
    """A descriptor for the hidden method."""

    __wrapped__: Callable[[I], T]
    """The wrapped function or method."""

    __slots__ = "hidden_method_name", "hidden_method_descriptor", "_fget"

    def __init__(
        _ModifiedMixin self,
        _fget: AsyncGetterFunction[I, T],
        field_name: Optional[str] = None,
        **modifiers: Unpack[ModifierKwargs],
    ) -> None:
        """Initializes the _ASyncPropertyDescriptorBase.

        Args:
            _fget: The function to be wrapped.
            field_name: Optional name for the field. If not provided, the function's name will be used.
            **modifiers: Additional modifier arguments.
        """
        cdef dict hidden_modifiers
        ASyncDescriptor.__init__(self, _fget, field_name, **modifiers)
        self.hidden_method_name = f"__{self.field_name}__"
        hidden_modifiers = self.modifiers._modifiers.copy()
        hidden_modifiers["default"] = "async"
        self.hidden_method_descriptor = HiddenMethodDescriptor(
            self.get, self.hidden_method_name, **hidden_modifiers
        )
        if iscoroutinefunction(_fget):
            self._fget = self.__wrapped__
        else:
            self._fget = _asyncify(self.__wrapped__, self.modifiers.executor)

    @overload
    def __get__(self, instance: None, owner: Type[I]) -> Self: ...
    @overload
    def __get__(self, instance: I, owner: Type[I]) -> Awaitable[T]: ...
    def __get__(
        self, instance: Optional[I], owner: Type[I]
    ) -> Union[Self, Awaitable[T]]:
        """Retrieves the property value, either synchronously or asynchronously.

        Args:
            instance: The instance from which the property is accessed.
            owner: The owner class of the property.

        Returns:
            The property value, either as an awaitable or directly.
        """
        if instance is None:
            return self
        
        cdef object awaitable = super().__get__(instance, owner)

        # if the user didn't specify a default behavior, we will defer to the instance
        cdef bint should_await
        cdef str default = _ModifiedMixin.get_default(self)
        if default:
            should_await = default == "sync"
        elif _is_a_sync_instance(instance):
            should_await = instance.__a_sync_instance_should_await__
        else:
            should_await = not get_event_loop().is_running()
        
        cdef object retval
        cdef bint debug_logs = _logger_is_enabled(DEBUG)
        if should_await:
            if debug_logs:
                _logger_log(
                    DEBUG,
                    "awaiting awaitable for %s for instance: %s owner: %s",
                    (awaitable, self, instance, owner),
                )
            retval = _await(awaitable)
        else:
            retval = awaitable

        if debug_logs:
            _logger_log(
                DEBUG,
                "returning %s for %s for instance: %s owner: %s",
                (retval, self, instance, owner), 
            )

        return retval

    async def get(self, instance: I, owner: Optional[Type[I]] = None) -> T:
        """Asynchronously retrieves the property value.

        Args:
            instance: The instance from which the property is accessed.
            owner: The owner class of the property.

        Returns:
            The property value.
        """
        _logger_debug("awaiting %s for instance %s", self, instance)
        return await super().__get__(instance, owner)

    def map(
        self,
        instances: AnyIterable[I],
        owner: Optional[Type[I]] = None,
        concurrency: Optional[int] = None,
        name: str = "",
    ) -> "TaskMapping[I, T]":
        """Maps the property across multiple instances.

        Args:
            instances: An iterable of instances.
            owner: The owner class of the property.
            concurrency: Optional concurrency limit.
            name: Optional name for the task mapping.

        Returns:
            A TaskMapping object.
        """
        _logger_debug("mapping %s to instances: %s owner: %s", self, instances, owner)
        
        """NOTE: This silly helper just fixes a circular import"""
        if TaskMapping is None:
            _import_TaskMapping()

        return TaskMapping(
            self,
            instances,
            owner=owner,
            name=name or self.field_name,
            concurrency=concurrency,
        )


class ASyncPropertyDescriptor(
    _ASyncPropertyDescriptorBase[I, T], ap.base.AsyncPropertyDescriptor
):
    """Descriptor class for asynchronous properties."""


class ASyncPropertyDescriptorSyncDefault(ASyncPropertyDescriptor[I, T]):
    """
    A variant of :class:`~ASyncPropertyDescriptor` that defaults to synchronous behavior.

    This class is used when the property is primarily intended to be accessed
    synchronously but can also be used asynchronously if needed.
    """

    # TODO give all of these docstrings
    default = "sync"
    # TODO and give these ones examples
    any: ASyncFunctionSyncDefault[AnyIterable[I], bool]
    all: ASyncFunctionSyncDefault[AnyIterable[I], bool]
    min: ASyncFunctionSyncDefault[AnyIterable[I], T]
    max: ASyncFunctionSyncDefault[AnyIterable[I], T]
    sum: ASyncFunctionSyncDefault[AnyIterable[I], T]

    @overload
    def __get__(self, instance: None, owner: Type[I]) -> Self: ...
    @overload
    def __get__(self, instance: I, owner: Type[I]) -> T: ...

    __get__ = _ASyncPropertyDescriptorBase.__get__
    """Retrieves the property value, either synchronously or asynchronously.

    Args:
        instance: The instance from which the property is accessed.
        owner: The owner class of the property.

    Returns:
        The property value, either as an awaitable or directly.
    """


class ASyncPropertyDescriptorAsyncDefault(ASyncPropertyDescriptor[I, T]):
    """
    A variant of :class:`~ASyncPropertyDescriptor` that defaults to asynchronous behavior.

    This class is used when the property is primarily intended to be accessed
    asynchronously but can also be used synchronously if needed.
    """

    # TODO give all of these docstrings
    default = "async"
    # TODO and give these ones examples
    any: ASyncFunctionAsyncDefault[AnyIterable[I], bool]
    all: ASyncFunctionAsyncDefault[AnyIterable[I], bool]
    min: ASyncFunctionAsyncDefault[AnyIterable[I], T]
    max: ASyncFunctionAsyncDefault[AnyIterable[I], T]
    sum: ASyncFunctionAsyncDefault[AnyIterable[I], T]


# Give all of these docstrings
ASyncPropertyDecorator = Callable[[AnyGetterFunction[I, T]], ASyncPropertyDescriptor[I, T]]
ASyncPropertyDecoratorSyncDefault = Callable[
    [AnyGetterFunction[I, T]], ASyncPropertyDescriptorSyncDefault[I, T]
]
ASyncPropertyDecoratorAsyncDefault = Callable[
    [AnyGetterFunction[I, T]], ASyncPropertyDescriptorAsyncDefault[I, T]
]


@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecorator[I, T]: ...


@overload
def a_sync_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDescriptor[I, T]: ...


@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorSyncDefault[I, T]: ...


@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorSyncDefault[I, T]: ...


@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorAsyncDefault[I, T]: ...


@overload
def a_sync_property(  # type: ignore [misc]
    func: Literal[None],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecorator[I, T]: ...


@overload
def a_sync_property(  # type: ignore [misc]
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorSyncDefault[I, T]: ...


@overload
def a_sync_property(  # type: ignore [misc]
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDecoratorAsyncDefault[I, T]: ...


@overload
def a_sync_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDescriptorSyncDefault[I, T]: ...


@overload
def a_sync_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDescriptorAsyncDefault[I, T]: ...


@overload
def a_sync_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncPropertyDescriptor[I, T]: ...


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
    """Decorator for creating properties that can be accessed both synchronously and asynchronously.

    Args:
        func: The function to be wrapped.
        **modifiers: Additional modifier arguments.

    Returns:
        A property descriptor that supports both sync and async access.
    """
    func, modifiers = _parse_args(func, <dict>modifiers)
    cdef object descriptor_class
    if (<dict>modifiers).get("default") == "sync":
        descriptor_class = ASyncPropertyDescriptorSyncDefault
    elif (<dict>modifiers).get("default") == "async":
        descriptor_class = ASyncPropertyDescriptorAsyncDefault
    else:
        descriptor_class = ASyncPropertyDescriptor
    decorator = partial(descriptor_class, **modifiers)
    return decorator if func is None else decorator(func)


class ASyncCachedPropertyDescriptor(
    _ASyncPropertyDescriptorBase[I, T], cached.AsyncCachedPropertyDescriptor
):
    """
    A descriptor class for dual-function sync/async cached properties.

    This class extends the API of ASyncPropertyDescriptor to provide
    caching functionality, storing the computed value after the first access.
    """

    __slots__ = "_fset", "_fdel", "__async_property__"

    def __init__(
        self,
        _fget: AsyncGetterFunction[I, T],
        _fset=None,
        _fdel=None,
        field_name=None,
        **modifiers: Unpack[ModifierKwargs],
    ) -> None:
        """Initializes the ASyncCachedPropertyDescriptor.

        Args:
            _fget: The function to be wrapped.
            _fset: Optional setter function for the property.
            _fdel: Optional deleter function for the property.
            field_name: Optional name for the field. If not provided, the function's name will be used.
            **modifiers: Additional modifier arguments.
        """
        _ASyncPropertyDescriptorBase.__init__(self, _fget, field_name, **modifiers)
        self._check_method_sync(_fset, "setter")
        self._fset = _fset
        """Optional setter function for the property."""

        self._check_method_sync(_fdel, "deleter")
        self._fdel = _fdel
        """Optional deleter function for the property."""

    def get_lock(self, instance: I) -> "Task[T]":
        """Retrieves the lock for the property.

        Args:
            instance: The instance from which the property is accessed.

        Returns:
            An asyncio Task representing the lock.
        """
        locks = (<AsyncCachedPropertyInstanceState>self.get_instance_state(instance)).locks 
        task = locks[self.field_name]
        if isinstance(task, Lock):
            # default behavior uses lock but we want to use a Task so all waiters wake up together
            task = ccreate_task_simple(self._fget(instance))
            locks[self.field_name] = task
        return task

    def get_loader(self, instance: I) -> Callable[[], T]:
        """Retrieves the loader function for the property.

        Args:
            instance: The instance from which the property is accessed.

        Returns:
            A callable that loads the property value.
        """
        cdef str field_name

        loader = self._load_value
        if loader is None:
            field_name = self.field_name

            @wraps(self._fget)
            async def loader(instance):
                cdef AsyncCachedPropertyInstanceState cache_state
                cache_state = self.get_instance_state(instance)

                inner_task = cache_state.locks[field_name]
                if isinstance(inner_task, Lock):
                    # default behavior uses lock but we want to use a Task so all waiters wake up together
                    inner_task = ccreate_task_simple(self._fget(instance))
                    cache_state.locks[field_name] = inner_task

                try:
                    value = await shield(inner_task)
                except Exception as e:
                    instance_context = {"property": self, "instance": instance}
                    if e.args and e.args[-1] != instance_context:
                        e.args = *e.args, instance_context
                    raise copy(e).with_traceback(e.__traceback__)
                
                if self._fset is not None:
                    self._fset(instance, value)
                
                if field_name not in cache_state.cache:
                    cache_state.cache[field_name] = value
                    cache_state.locks.pop(field_name)
                
                return value

            self._load_value = loader

        return lambda: loader(instance)


class ASyncCachedPropertyDescriptorSyncDefault(ASyncCachedPropertyDescriptor[I, T]):
    """
    A variant of :class:`~ASyncCachedPropertyDescriptor` that defaults to synchronous behavior.

    This class is used for cached properties that are primarily intended to be
    accessed synchronously but can also be used asynchronously if needed.

    Note:
        You should never create these yourself. They are automatically generated by ez-a-sync internally.
    """

    default: Literal["sync"]

    @overload
    def __get__(self, instance: None, owner: Type[I]) -> Self: ...
    @overload
    def __get__(self, instance: I, owner: Type[I]) -> T: ...

    __get__ = _ASyncPropertyDescriptorBase.__get__
    """Retrieves the cached property value, either synchronously or asynchronously.

    Args:
        instance: The instance from which the property is accessed.
        owner: The owner class of the property.

    Returns:
        The cached property value, either as an awaitable or directly.
    """


class ASyncCachedPropertyDescriptorAsyncDefault(ASyncCachedPropertyDescriptor[I, T]):
    """
    A variant of :class:`~ASyncCachedPropertyDescriptor` that defaults to asynchronous behavior.

    This class is used for cached properties that are primarily intended to be
    accessed asynchronously but can also be used synchronously if needed.

    Note:
        You should never create these yourself. They are automatically generated by ez-a-sync internally.
    """

    default: Literal["async"]


ASyncCachedPropertyDecorator = Callable[
    [AnyGetterFunction[I, T]], ASyncCachedPropertyDescriptor[I, T]
]
ASyncCachedPropertyDecoratorSyncDefault = Callable[
    [AnyGetterFunction[I, T]], ASyncCachedPropertyDescriptorSyncDefault[I, T]
]
ASyncCachedPropertyDecoratorAsyncDefault = Callable[
    [AnyGetterFunction[I, T]], ASyncCachedPropertyDescriptorAsyncDefault[I, T]
]


@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecorator[I, T]: ...


@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDescriptor[I, T]: ...


@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecoratorSyncDefault[I, T]: ...


@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecoratorAsyncDefault[I, T]: ...


@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: Literal[None],
    default: DefaultMode,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecorator[I, T]: ...


@overload
def a_sync_cached_property(  # type: ignore [misc]
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecoratorSyncDefault[I, T]: ...


@overload
def a_sync_cached_property(  # type: ignore [misc]
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDecoratorAsyncDefault[I, T]: ...


@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDescriptorSyncDefault[I, T]: ...


@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDescriptorAsyncDefault[I, T]: ...


@overload
def a_sync_cached_property(  # type: ignore [misc]
    func: AnyGetterFunction[I, T],
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncCachedPropertyDescriptor[I, T]: ...


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
    """Decorator for creating cached properties that can be accessed both synchronously and asynchronously.

    Args:
        func: The function to be wrapped.
        **modifiers: Additional modifier arguments.

    Returns:
        A cached property descriptor that supports both sync and async access.
    """
    func, modifiers = _parse_args(func, <dict>modifiers)
    cdef object descriptor_class
    if (<dict>modifiers).get("default") == "sync":
        descriptor_class = ASyncCachedPropertyDescriptorSyncDefault
    elif (<dict>modifiers).get("default") == "async":
        descriptor_class = ASyncCachedPropertyDescriptorAsyncDefault
    else:
        descriptor_class = ASyncCachedPropertyDescriptor
    decorator = partial(descriptor_class, **modifiers)
    return decorator if func is None else decorator(func)


class HiddenMethod(ASyncBoundMethodAsyncDefault[I, Tuple[()], T]):
    """Represents a hidden method for asynchronous properties.

    This class is used internally to manage hidden getter methods associated with a/sync properties.

    Note:
        You should never create these yourself. They are automatically generated by ez-a-sync internally.
    """

    def __init__(
        self,
        instance: I,
        unbound: AnyFn[Concatenate[I, P], T],
        async_def: bool,
        field_name: str,
        **modifiers: Unpack[ModifierKwargs],
    ) -> None:
        """Initializes the HiddenMethod.

        Args:
            instance: The instance to which the method is bound.
            unbound: The unbound function to be wrapped.
            async_def: Indicates if the method is asynchronous.
            field_name: The name of the field associated with the method.
            **modifiers: Additional modifier arguments.
        """
        # TODO: copy __init_subclass__ to this class and then use _ASyncBoundMethod.__init__ instead
        ASyncBoundMethod.__init__(self, instance, unbound, async_def, **modifiers)
        self.__name__ = field_name
        """The name of the hidden method."""

    def __repr__(_ASyncBoundMethod self) -> str:
        """Returns a string representation of the HiddenMethod."""
        instance = self.__c_self__()
        instance_type = type(instance)
        return "<{} for property {}.{}.{} bound to {}>".format(
            self.__class__.__name__,
            instance_type.__module__,
            instance_type.__name__,
            self.__name__[2:-2],
            instance,
        )

    def __await__(_ASyncBoundMethod self) -> Generator[Any, None, T]:
        """Returns an awaitable for the method."""
        # NOTE: self(sync=False).__await__() would be cleaner but requires way more compute for no real gain
        _logger_debug("awaiting %s", self)
        return self.get_fn()(self.__c_self__(), sync=False).__await__()


class HiddenMethodDescriptor(ASyncMethodDescriptorAsyncDefault[I, Tuple[()], T]):
    """Descriptor for hidden methods associated with asynchronous properties.

    This class is used internally to manage hidden getter methods associated with a/sync properties.

    Note:
        You should never create these yourself. They are automatically generated by ez-a-sync internally.
    """

    def __init__(
        self,
        _fget: AnyFn[Concatenate[I, P], Awaitable[T]],
        field_name: Optional[str] = None,
        **modifiers: Unpack[ModifierKwargs],
    ) -> None:
        """
        Initialize the HiddenMethodDescriptor.

        Args:
            _fget: The function to be wrapped.
            field_name: Optional name for the field. If not provided, the function's name will be used.
            **modifiers: Additional modifier arguments.

        Raises:
            ValueError: If _fget is not callable.
        """
        ASyncDescriptor.__init__(self, _fget, field_name, **modifiers)
        if self.__doc__ is None:
            self.__doc__ = f"A :class:`HiddenMethodDescriptor` for :meth:`{self.__wrapped__.__qualname__}`."
        elif not self.__doc__:
            self.__doc__ += f"A :class:`HiddenMethodDescriptor` for :meth:`{self.__wrapped__.__qualname__}`."
        if self.__wrapped__.__doc__:
            self.__doc__ += f"\n\nThe original docstring for :meth:`~{self.__wrapped__.__qualname__}` is shown below:\n\n{self.__wrapped__.__doc__}"

    def __get__(_ModifiedMixin self, instance: I, owner: Type[I]) -> HiddenMethod[I, T]:
        """Retrieves the hidden method for the property.

        Args:
            instance: The instance from which the method is accessed.
            owner: The owner class of the method.

        Returns:
            The hidden method.
        """
        if instance is None:
            return self
    
        cdef _ASyncBoundMethod bound
        cdef str field_name = self.field_name
        try:
            bound = instance.__dict__[field_name]
        except KeyError:
            bound = HiddenMethod(
                instance,
                self.__wrapped__,
                self.__is_async_def__,
                field_name,
                **self.modifiers._modifiers,
            )
            instance.__dict__[field_name] = bound
            _logger_debug("new hidden method: %s", bound)
        _update_cache_timer(field_name, instance, bound)
        return bound


cdef object _parse_args(
    func: Union[None, DefaultMode, AsyncGetterFunction[I, T]], 
    dict modifiers,
):
    """Parses the arguments for the property decorators.

    Args:
        func: The function to be wrapped.
        modifiers: Additional modifier arguments.

    Returns:
        Tuple[Optional[AsyncGetterFunction[I, T]], ModifierKwargs] A tuple containing the parsed function and modifiers.
    """
    if func in ("sync", "async"):
        modifiers["default"] = func
        return None, modifiers
    return func, modifiers


cdef inline void _import_TaskMapping():
    global TaskMapping
    from a_sync import TaskMapping
