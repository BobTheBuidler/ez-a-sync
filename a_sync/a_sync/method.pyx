"""
This module provides classes for implementing dual-functional sync/async methods in Python.

It includes descriptors and bound methods that can be used to create flexible
asynchronous interfaces, allowing methods to be called both synchronously and
asynchronously based on various conditions and configurations.
"""

# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc
import functools
import heapq
import logging
import weakref
from inspect import isawaitable

from a_sync import exceptions
from a_sync._typing import *
from a_sync.a_sync import _helpers, _kwargs
from a_sync.a_sync._descriptor import ASyncDescriptor
from a_sync.a_sync.function import (
    ASyncFunction,
    ASyncFunctionAsyncDefault,
    ASyncFunctionSyncDefault,
)

if TYPE_CHECKING:
    from a_sync import TaskMapping
    from a_sync.a_sync.abstract import ASyncABC


METHOD_CACHE_TTL = 300

logger = logging.getLogger(__name__)


class ASyncMethodDescriptor(ASyncDescriptor[I, P, T]):
    """
    A descriptor for managing methods that can be called both synchronously and asynchronously.

    This class provides the core functionality for binding methods to instances and determining
    the execution mode ("sync" or "async") based on various conditions, such as the instance type,
    the method's default setting, or specific flags passed during the method call.

    The descriptor is responsible for creating an appropriate bound method when accessed,
    which is the actual object that can be called in both synchronous and asynchronous contexts.
    It can create different types of bound methods (`ASyncBoundMethodSyncDefault`,
    `ASyncBoundMethodAsyncDefault`, or `ASyncBoundMethod`) based on the default mode or instance type.

    If the default mode is explicitly set to "sync" or "async", it creates `ASyncBoundMethodSyncDefault`
    or `ASyncBoundMethodAsyncDefault` respectively. If neither is set, it defaults to creating an
    `ASyncBoundMethod`. For instances of :class:`ASyncABC`, it checks the `__a_sync_instance_should_await__`
    attribute to decide the type of bound method to create.

    It also manages cache handles for bound methods and prevents setting or deleting the descriptor.

    Examples:
        >>> class MyClass:
        ...     @ASyncMethodDescriptor
        ...     async def my_method(self):
        ...         return "Hello, World!"
        ...
        >>> obj = MyClass()
        >>> await obj.my_method()
        'Hello, World!'
        >>> obj.my_method(sync=True)
        'Hello, World!'

    See Also:
        - :class:`ASyncBoundMethod`
        - :class:`ASyncFunction`
    """

    __wrapped__: AnyFn[P, T]
    """The unbound function which will be bound to an instance when :meth:`__get__` is called."""

    async def __call__(self, instance: I, *args: P.args, **kwargs: P.kwargs) -> T:
        """
        Asynchronously call the method.

        Args:
            instance: The instance the method is bound to.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Examples:
            >>> descriptor = ASyncMethodDescriptor(my_async_function)
            >>> await descriptor(instance, arg1, arg2, kwarg1=value1)
        """
        # NOTE: This is only used by TaskMapping atm  # TODO: use it elsewhere
        logger.debug(
            "awaiting %s for instance: %s args: %s kwargs: %s",
            self,
            instance,
            args,
            kwargs,
        )
        return await self.__get__(instance, None)(*args, **kwargs)

    @overload
    def __get__(self, instance: None, owner: Type[I]) -> Self: ...
    @overload
    def __get__(self, instance: I, owner: Type[I]) -> "ASyncBoundMethod[I, P, T]": ...
    def __get__(
        self, instance: Optional[I], owner: Type[I]
    ) -> Union[Self, "ASyncBoundMethod[I, P, T]"]:
        """
        Get the bound method or the descriptor itself.

        Args:
            instance: The instance to bind the method to, or None.
            owner: The owner class.

        Examples:
            >>> descriptor = ASyncMethodDescriptor(my_function)
            >>> bound_method = descriptor.__get__(instance, MyClass)
        """
        if instance is None:
            return self
        try:
            bound = instance.__dict__[self.field_name]
            # we will set a new one in the finally block
            bound._cache_handle.cancel()
        except KeyError:
            from a_sync.a_sync.abstract import ASyncABC

            if self.default == "sync":
                bound = ASyncBoundMethodSyncDefault(
                    instance, self.__wrapped__, self.__is_async_def__, **self.modifiers
                )
            elif self.default == "async":
                bound = ASyncBoundMethodAsyncDefault(
                    instance, self.__wrapped__, self.__is_async_def__, **self.modifiers
                )
            elif isinstance(instance, ASyncABC):
                try:
                    if instance.__a_sync_instance_should_await__:
                        bound = ASyncBoundMethodSyncDefault(
                            instance,
                            self.__wrapped__,
                            self.__is_async_def__,
                            **self.modifiers,
                        )
                    else:
                        bound = ASyncBoundMethodAsyncDefault(
                            instance,
                            self.__wrapped__,
                            self.__is_async_def__,
                            **self.modifiers,
                        )
                except AttributeError:
                    bound = ASyncBoundMethod(
                        instance,
                        self.__wrapped__,
                        self.__is_async_def__,
                        **self.modifiers,
                    )
            else:
                bound = ASyncBoundMethod(
                    instance, self.__wrapped__, self.__is_async_def__, **self.modifiers
                )
            instance.__dict__[self.field_name] = bound
            logger.debug("new bound method: %s", bound)
        _update_cache_timer(self.field_name, instance, bound)
        return bound

    def __set__(self, instance, value):
        """
        Prevent setting the descriptor.

        Args:
            instance: The instance.
            value: The value to set.

        Raises:
            RuntimeError: Always raised to prevent setting.

        Examples:
            >>> descriptor = ASyncMethodDescriptor(my_function)
            >>> descriptor.__set__(instance, value)
            RuntimeError: cannot set field_name, descriptor is what you get. sorry.
        """
        raise RuntimeError(
            f"cannot set {self.field_name}, {self} is what you get. sorry."
        )

    def __delete__(self, instance):
        """
        Prevent deleting the descriptor.

        Args:
            instance: The instance.

        Raises:
            RuntimeError: Always raised to prevent deletion.

        Examples:
            >>> descriptor = ASyncMethodDescriptor(my_function)
            >>> descriptor.__delete__(instance)
            RuntimeError: cannot delete field_name, you're stuck with descriptor forever. sorry.
        """
        raise RuntimeError(
            f"cannot delete {self.field_name}, you're stuck with {self} forever. sorry."
        )

    @functools.cached_property
    def __is_async_def__(self) -> bool:
        """
        Check if the wrapped function is a coroutine function.

        Examples:
            >>> descriptor = ASyncMethodDescriptor(my_function)
            >>> descriptor.__is_async_def__
            True
        """
        return asyncio.iscoroutinefunction(self.__wrapped__)


cdef void _update_cache_timer(field_name: str, instance: I, bound: "ASyncBoundMethod"):
    """
    Update the TTL for the cache handle for the instance.

    Args:
        instance: The instance to create a cache handle for.
        bound: The bound method we are caching.
    """
    # Handler for popping unused bound methods from bound method cache
    cdef object handle, loop
    if handle := bound._cache_handle:
        # update the timer handle
        handle._when = handle._loop.time() + METHOD_CACHE_TTL
    else:
        # create and assign the timer handle
        loop = asyncio.get_event_loop()
        # NOTE: use `instance.__dict__.pop` instead of `delattr` so we don't create a strong ref to `instance`
        bound._cache_handle = loop.call_at(loop.time() + METHOD_CACHE_TTL, instance.__dict__.pop, field_name)


@final
class ASyncMethodDescriptorSyncDefault(ASyncMethodDescriptor[I, P, T]):
    """
    A descriptor for :class:`ASyncBoundMethodSyncDefault` objects.

    This class extends :class:`ASyncMethodDescriptor` to provide a synchronous
    default behavior for method calls. It specifically creates `ASyncBoundMethodSyncDefault`
    instances, which are specialized versions of `ASyncBoundMethod` with synchronous default behavior.

    Examples:
        >>> class MyClass:
        ...     @ASyncMethodDescriptorSyncDefault
        ...     def my_method(self):
        ...         return "Hello, World!"
        ...
        >>> obj = MyClass()
        >>> obj.my_method()
        'Hello, World!'
        >>> coro = obj.my_method(sync=False)
        >>> coro
        <coroutine object MyClass.my_method at 0x7fb4f5fb49c0>
        >>> await coro
        'Hello, World!'

    See Also:
        - :class:`ASyncBoundMethodSyncDefault`
        - :class:`ASyncFunctionSyncDefault`
    """

    default = "sync"
    """The default mode for this bound method. Always set to "sync"."""

    any: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], bool]
    """Synchronous default version of the :meth:`~ASyncMethodDescriptor.any` method."""

    all: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], bool]
    """Synchronous default version of the :meth:`~ASyncMethodDescriptor.all` method."""

    min: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], T]
    """Synchronous default version of the :meth:`~ASyncMethodDescriptor.min` method."""

    max: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], T]
    """Synchronous default version of the :meth:`~ASyncMethodDescriptor.max` method."""

    sum: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], T]
    """Synchronous default version of the :meth:`~ASyncMethodDescriptor.sum` method."""

    @overload
    def __get__(
        self, instance: None, owner: Type[I] = None
    ) -> "ASyncMethodDescriptorSyncDefault[I, P, T]": ...
    @overload
    def __get__(
        self, instance: I, owner: Type[I] = None
    ) -> "ASyncBoundMethodSyncDefault[I, P, T]": ...
    def __get__(
        self, instance: Optional[I], owner: Type[I] = None
    ) -> (
        "Union[ASyncMethodDescriptorSyncDefault, ASyncBoundMethodSyncDefault[I, P, T]]"
    ):
        """
        Get the bound method or the descriptor itself.

        Args:
            instance: The instance to bind the method to, or None.
            owner: The owner class.

        Examples:
            >>> descriptor = ASyncMethodDescriptorSyncDefault(my_function)
            >>> bound_method = descriptor.__get__(instance, MyClass)
        """
        if instance is None:
            return self
        try:
            bound = instance.__dict__[self.field_name]
            # we will set a new one in the finally block
            bound._cache_handle.cancel()
        except KeyError:
            bound = ASyncBoundMethodSyncDefault(
                instance, self.__wrapped__, self.__is_async_def__, **self.modifiers
            )
            instance.__dict__[self.field_name] = bound
            logger.debug("new bound method: %s", bound)
        _update_cache_timer(self.field_name, instance, bound)
        return bound


@final
class ASyncMethodDescriptorAsyncDefault(ASyncMethodDescriptor[I, P, T]):
    """
    A descriptor for asynchronous methods with an asynchronous default.

    This class extends :class:`ASyncMethodDescriptor` to provide an asynchronous default
    behavior for method calls. It specifically creates `ASyncBoundMethodAsyncDefault`
    instances, which are specialized versions of `ASyncBoundMethod` with asynchronous default behavior.

    Examples:
        >>> class MyClass:
        ...     @ASyncMethodDescriptorAsyncDefault
        ...     async def my_method(self):
        ...         return "Hello, World!"
        ...
        >>> obj = MyClass()
        >>> coro = obj.my_method()
        >>> coro
        <coroutine object MyClass.my_method at 0x7fb4f5fb49c0>
        >>> await coro
        >>> obj.my_method(sync=True)
        'Hello, World!'

    See Also:
        - :class:`ASyncBoundMethodAsyncDefault`
        - :class:`ASyncFunctionAsyncDefault`
    """

    default = "async"
    """The default mode for this bound method. Always set to "async"."""

    any: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], bool]
    """Asynchronous default version of the :meth:`~ASyncMethodDescriptor.any` method."""

    all: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], bool]
    """Asynchronous default version of the :meth:`~ASyncMethodDescriptor.all` method."""

    min: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], T]
    """Asynchronous default version of the :meth:`~ASyncMethodDescriptor.min` method."""

    max: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], T]
    """Asynchronous default version of the :meth:`~ASyncMethodDescriptor.max` method."""

    sum: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], T]
    """Asynchronous default version of the :meth:`~ASyncMethodDescriptor.sum` method."""

    @overload
    def __get__(
        self, instance: None, owner: Type[I]
    ) -> "ASyncMethodDescriptorAsyncDefault[I, P, T]": ...
    @overload
    def __get__(
        self, instance: I, owner: Type[I]
    ) -> "ASyncBoundMethodAsyncDefault[I, P, T]": ...
    def __get__(
        self, instance: Optional[I], owner: Type[I]
    ) -> "Union[ASyncMethodDescriptorAsyncDefault, ASyncBoundMethodAsyncDefault[I, P, T]]":
        """
        Get the bound method or the descriptor itself.

        Args:
            instance: The instance to bind the method to, or None.
            owner: The owner class.

        Examples:
            >>> descriptor = ASyncMethodDescriptorAsyncDefault(my_function)
            >>> bound_method = descriptor.__get__(instance, MyClass)
        """
        if instance is None:
            return self
        try:
            bound = instance.__dict__[self.field_name]
            # we will set a new one in the finally block
            bound._cache_handle.cancel()
        except KeyError:
            bound = ASyncBoundMethodAsyncDefault(
                instance, self.__wrapped__, self.__is_async_def__, **self.modifiers
            )
            instance.__dict__[self.field_name] = bound
            logger.debug("new bound method: %s", bound)
        _update_cache_timer(self.field_name, instance, bound)
        return bound


class ASyncBoundMethod(ASyncFunction[P, T], Generic[I, P, T]):
    """
    A bound method that can be called both synchronously and asynchronously.

    This class represents a method bound to an instance, which can be called
    either synchronously or asynchronously based on various conditions. It handles
    caching of bound methods and includes logic for determining whether to await
    the method call based on flags or default settings.

    Examples:
        >>> class MyClass:
        ...     def __init__(self, value):
        ...         self.value = value
        ...
        ...     @ASyncMethodDescriptor
        ...     async def my_method(self):
        ...         return self.value
        ...
        >>> obj = MyClass(42)
        >>> await obj.my_method()
        42
        >>> obj.my_method(sync=True)
        42

    See Also:
        - :class:`ASyncMethodDescriptor`
        - :class:`ASyncFunction`
    """

    # NOTE: this is created by the Descriptor

    _cache_handle: asyncio.TimerHandle = None
    """An asyncio handle used to pop the bound method from `instance.__dict__` 5 minutes after its last use."""

    __weakself__: "weakref.ref[I]"
    """A weak reference to the instance the function is bound to."""

    __wrapped__: AnyFn[Concatenate[I, P], T]
    """The original unbound method that was wrapped."""

    __slots__ = "_is_async_def", "__weakself__"

    def __init__(
        self,
        instance: I,
        unbound: AnyFn[Concatenate[I, P], T],
        async_def: bool,
        **modifiers: Unpack[ModifierKwargs],
    ) -> None:
        """
        Initialize the bound method.

        Args:
            instance: The instance to bind the method to.
            unbound: The unbound function.
            async_def: Whether the original function is an async def.
            **modifiers: Additional modifiers for the function.

        Examples:
            >>> class MyClass:
            ...     def __init__(self, value):
            ...         self.value = value
            ...
            ...     @ASyncMethodDescriptor
            ...     async def my_method(self):
            ...         return self.value
            ...
            >>> obj = MyClass(42)
            >>> bound_method = ASyncBoundMethod(obj, MyClass.my_method, True)
        """
        self.__weakself__ = weakref.ref(instance, self.__cancel_cache_handle)
        # First we unwrap the coro_fn and rewrap it so overriding flag kwargs are handled automagically.
        if isinstance(unbound, ASyncFunction):
            modifiers.update(unbound.modifiers)
            unbound = unbound.__wrapped__
        # NOTE: the wrapped function was validated when the descriptor was initialized
        ASyncFunction.__init__(self, unbound, _skip_validate=True, **modifiers)
        self._is_async_def = async_def
        """True if `self.__wrapped__` is a coroutine function, False otherwise."""
        functools.update_wrapper(self, unbound)

    def __repr__(self) -> str:
        """
        Return a string representation of the bound method.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> repr(bound_method)
            '<ASyncBoundMethod for function module.ClassName.method_name bound to instance>'
        """
        try:
            instance_type = type(self.__self__)
            return "<{} for function {}.{}.{} bound to {}>".format(
                self.__class__.__name__,
                instance_type.__module__,
                instance_type.__name__,
                self.__name__,
                self.__self__
            )
        except ReferenceError:
            return "<{} for function COLLECTED.COLLECTED.{} bound to {}>".format(
                self.__class__.__name__,
                self.__name__,
                self.__weakself__
            )

    @overload
    def __call__(self, *args: P.args, sync: Literal[True], **kwargs: P.kwargs) -> T: ...
    @overload
    def __call__(
        self, *args: P.args, sync: Literal[False], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]: ...
    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs
    ) -> T: ...
    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[True], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]: ...
    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MaybeCoro[T]: ...
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MaybeCoro[T]:
        """
        Call the bound method.

        This method handles both synchronous and asynchronous calls based on
        the provided flags and the method's configuration.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> await bound_method(arg1, arg2, kwarg1=value1)
            >>> bound_method(arg1, arg2, kwarg1=value1, sync=True)
        """
        cdef object retval, coro
        logger.debug("calling %s with args: %s kwargs: %s", self, args, kwargs)
        # This could either be a coroutine or a return value from an awaited coroutine,
        #   depending on if an overriding flag kwarg was passed into the function call.
        retval = coro = ASyncFunction.__call__(self, self.__self__, *args, **kwargs)
        if not isawaitable(retval):
            # The coroutine was already awaited due to the use of an overriding flag kwarg.
            # We can return the value.
            pass
        elif self._should_await(kwargs):
            # The awaitable was not awaited, so now we need to check the flag as defined on 'self' and await if appropriate.
            logger.debug(
                "awaiting %s for %s args: %s kwargs: %s", coro, self, args, kwargs
            )
            retval = _helpers._await(coro)
        logger.debug(
            "returning %s for %s args: %s kwargs: %s", retval, self, args, kwargs
        )
        return retval  # type: ignore [call-overload, return-value]

    @property
    def __self__(self) -> I:
        """
        Get the instance the method is bound to.

        Raises:
            ReferenceError: If the instance has been garbage collected.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> bound_method.__self__
            <MyClass instance>
        """
        cdef object instance
        instance = self.__weakself__()
        if instance is not None:
            return instance
        raise ReferenceError(self)

    @functools.cached_property
    def __bound_to_a_sync_instance__(self) -> bool:
        """
        Check if the method is bound to an ASyncABC instance.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> bound_method.__bound_to_a_sync_instance__
            True
        """
        from a_sync.a_sync.abstract import ASyncABC

        return isinstance(self.__self__, ASyncABC)

    def map(
        self,
        *iterables: AnyIterable[I],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **kwargs: P.kwargs,
    ) -> "TaskMapping[I, T]":
        """
        Create a TaskMapping for this method.

        Args:
            *iterables: Iterables to map over.
            concurrency: Optional concurrency limit.
            task_name: Optional name for the task.
            **kwargs: Additional keyword arguments.

        Returns:
            A TaskMapping instance for this method.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> task_mapping = bound_method.map(iterable1, iterable2, concurrency=5)
            TODO briefly include how someone would then use task_mapping
        """
        from a_sync import TaskMapping

        return TaskMapping(
            self, *iterables, concurrency=concurrency, name=task_name, **kwargs
        )

    async def any(
        self,
        *iterables: AnyIterable[I],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **kwargs: P.kwargs,
    ) -> bool:
        """
        Check if any of the results are truthy.

        Args:
            *iterables: Iterables to map over.
            concurrency: Optional concurrency limit.
            task_name: Optional name for the task.
            **kwargs: Additional keyword arguments.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> result = await bound_method.any(iterable1, iterable2)
        """
        return await self.map(
            *iterables, concurrency=concurrency, task_name=task_name, **kwargs
        ).any(pop=True, sync=False)

    async def all(
        self,
        *iterables: AnyIterable[I],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **kwargs: P.kwargs,
    ) -> bool:
        """
        Check if all of the results are truthy.

        Args:
            *iterables: Iterables to map over.
            concurrency: Optional concurrency limit.
            task_name: Optional name for the task.
            **kwargs: Additional keyword arguments.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> result = await bound_method.all(iterable1, iterable2)
        """
        return await self.map(
            *iterables, concurrency=concurrency, task_name=task_name, **kwargs
        ).all(pop=True, sync=False)

    async def min(
        self,
        *iterables: AnyIterable[I],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **kwargs: P.kwargs,
    ) -> T:
        """
        Find the minimum result.

        Args:
            *iterables: Iterables to map over.
            concurrency: Optional concurrency limit.
            task_name: Optional name for the task.
            **kwargs: Additional keyword arguments.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> result = await bound_method.min(iterable1, iterable2)
        """
        return await self.map(
            *iterables, concurrency=concurrency, task_name=task_name, **kwargs
        ).min(pop=True, sync=False)

    async def max(
        self,
        *iterables: AnyIterable[I],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **kwargs: P.kwargs,
    ) -> T:
        """
        Find the maximum result.

        Args:
            *iterables: Iterables to map over.
            concurrency: Optional concurrency limit.
            task_name: Optional name for the task.
            **kwargs: Additional keyword arguments.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> result = await bound_method.max(iterable1, iterable2)
        """
        return await self.map(
            *iterables, concurrency=concurrency, task_name=task_name, **kwargs
        ).max(pop=True, sync=False)

    async def sum(
        self,
        *iterables: AnyIterable[I],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **kwargs: P.kwargs,
    ) -> T:
        """
        Calculate the sum of the results.

        Args:
            *iterables: Iterables to map over.
            concurrency: Optional concurrency limit.
            task_name: Optional name for the task.
            **kwargs: Additional keyword arguments.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> result = await bound_method.sum(iterable1, iterable2)
        """
        return await self.map(
            *iterables, concurrency=concurrency, task_name=task_name, **kwargs
        ).sum(pop=True, sync=False)

    def _should_await(self, dict kwargs) -> bint:
        """
        Determine if the method should be awaited.

        Args:
            kwargs: Keyword arguments passed to the method.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> should_await = bound_method._should_await(kwargs)
        """
        cdef object flag
        if flag := _kwargs.get_flag_name(kwargs):
            return _kwargs.is_sync(<str>flag, kwargs, pop_flag=True)  # type: ignore [arg-type]
        elif self.default:
            return self.default == "sync"
        elif self.__bound_to_a_sync_instance__:
            self.__self__: "ASyncABC"
            return self.__self__.__a_sync_should_await__(kwargs)
        return self._is_async_def

    def __cancel_cache_handle(self, object instance) -> None:
        """
        Cancel the cache handle.

        Args:
            instance: The instance associated with the cache handle.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> bound_method.__cancel_cache_handle(instance)
        """
        try:
            self._cache_handle.cancel()
        except AttributeError:
            # this runs if _cache_handle is None
            return


class ASyncBoundMethodSyncDefault(ASyncBoundMethod[I, P, T]):
    """
    A bound method with synchronous default behavior.

    This class is a specialized version of :class:`ASyncBoundMethod` that defaults to synchronous execution.
    It overrides the `__call__` method to enforce synchronous default behavior.

    Examples:
        >>> class MyClass:
        ...     def __init__(self, value):
        ...         self.value = value
        ...
        ...     @ASyncMethodDescriptorSyncDefault
        ...     def my_method(self):
        ...         return self.value
        ...
        >>> obj = MyClass(42)
        >>> obj.my_method()
        42
        >>> await obj.my_method(sync=False)
        42

    See Also:
        - :class:`ASyncBoundMethod`
        - :class:`ASyncMethodDescriptorSyncDefault`
    """

    @overload
    def __call__(self, *args: P.args, sync: Literal[True], **kwargs: P.kwargs) -> T: ...
    @overload
    def __call__(
        self, *args: P.args, sync: Literal[False], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]: ...
    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs
    ) -> T: ...
    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[True], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]: ...
    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T: ...

    __call__ = ASyncBoundMethod.__call__
    """
    Call the bound method with synchronous default behavior.

    Args:
        *args: Positional arguments.
        **kwargs: Keyword arguments.

    Examples:
        >>> bound_method = ASyncBoundMethodSyncDefault(instance, my_function, True)
        >>> bound_method(arg1, arg2, kwarg1=value1)
    """


class ASyncBoundMethodAsyncDefault(ASyncBoundMethod[I, P, T]):
    """
    A bound method with asynchronous default behavior.

    This class is a specialized version of :class:`ASyncBoundMethod` that defaults to asynchronous execution.
    It overrides the `__call__` method to enforce asynchronous default behavior.

    Examples:
        >>> class MyClass:
        ...     def __init__(self, value):
        ...         self.value = value
        ...
        ...     @ASyncMethodDescriptorAsyncDefault
        ...     async def my_method(self):
        ...         return self.value
        ...
        >>> obj = MyClass(42)
        >>> await obj.my_method()
        42
        >>> obj.my_method(sync=True)
        42

    See Also:
        - :class:`ASyncBoundMethod`
        - :class:`ASyncMethodDescriptorAsyncDefault`
    """

    @overload
    def __call__(self, *args: P.args, sync: Literal[True], **kwargs: P.kwargs) -> T: ...
    @overload
    def __call__(
        self, *args: P.args, sync: Literal[False], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]: ...
    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs
    ) -> T: ...
    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[True], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]: ...
    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Coroutine[Any, Any, T]: ...

    __call__ = ASyncBoundMethod.__call__
    """
    Call the bound method with asynchronous default behavior.

    Args:
        *args: Positional arguments.
        **kwargs: Keyword arguments.

    Examples:
        >>> bound_method = ASyncBoundMethodAsyncDefault(instance, my_function, True)
        >>> await bound_method(arg1, arg2, kwarg1=value1)
    """
