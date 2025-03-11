"""
This module provides classes for implementing dual-functional sync/async methods in Python.

It includes descriptors and bound methods that can be used to create flexible
asynchronous interfaces, allowing methods to be called both synchronously and
asynchronously based on various conditions and configurations.
"""

from a_sync._typing import *
import functools
import weakref
from _typeshed import Incomplete
from a_sync import TaskMapping as TaskMapping
from a_sync.a_sync._descriptor import ASyncDescriptor as ASyncDescriptor
from a_sync.a_sync.abstract import ASyncABC as ASyncABC
from a_sync.a_sync.function import (
    ASyncFunction as ASyncFunction,
    ASyncFunctionAsyncDefault as ASyncFunctionAsyncDefault,
    ASyncFunctionSyncDefault as ASyncFunctionSyncDefault,
)
from typing import Any

METHOD_CACHE_TTL: Literal[3600]
logger: Incomplete

class ASyncMethodDescriptor(ASyncDescriptor[I, P, T]):
    """
    A descriptor for managing methods that can be called both synchronously and asynchronously.

    This class provides the core functionality for binding methods to instances and determining
    the execution mode ("sync" or "async") based on various conditions, such as the instance type,
    the method\'s default setting, or specific flags passed during the method call.

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
        \'Hello, World!\'
        >>> obj.my_method(sync=True)
        \'Hello, World!\'

    See Also:
        - :class:`ASyncBoundMethod`
        - :class:`ASyncFunction`
    """

    __wrapped__: AnyFn[P, T]
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

    @overload
    def __get__(self, instance: None, owner: Type[I]) -> Self: ...
    @overload
    def __get__(self, instance: I, owner: Type[I]) -> ASyncBoundMethod[I, P, T]: ...
    def __set__(self, instance, value) -> None:
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

    def __delete__(self, instance) -> None:
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

    @functools.cached_property
    def __is_async_def__(self) -> bool:
        """
        Check if the wrapped function is a coroutine function.

        Examples:
            >>> descriptor = ASyncMethodDescriptor(my_function)
            >>> descriptor.__is_async_def__
            True
        """

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
        \'Hello, World!\'
        >>> coro = obj.my_method(sync=False)
        >>> coro
        <coroutine object MyClass.my_method at 0x7fb4f5fb49c0>
        >>> await coro
        \'Hello, World!\'

    See Also:
        - :class:`ASyncBoundMethodSyncDefault`
        - :class:`ASyncFunctionSyncDefault`
    """

    default: str
    any: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], bool]
    all: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], bool]
    min: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], T]
    max: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], T]
    sum: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], T]
    @overload
    def __get__(
        self, instance: None, owner: Type[I] = None
    ) -> ASyncMethodDescriptorSyncDefault[I, P, T]: ...
    @overload
    def __get__(
        self, instance: I, owner: Type[I] = None
    ) -> ASyncBoundMethodSyncDefault[I, P, T]: ...

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
        \'Hello, World!\'

    See Also:
        - :class:`ASyncBoundMethodAsyncDefault`
        - :class:`ASyncFunctionAsyncDefault`
    """

    default: str
    any: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], bool]
    all: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], bool]
    min: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], T]
    max: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], T]
    sum: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], T]
    @overload
    def __get__(
        self, instance: None, owner: Type[I]
    ) -> ASyncMethodDescriptorAsyncDefault[I, P, T]: ...
    @overload
    def __get__(self, instance: I, owner: Type[I]) -> ASyncBoundMethodAsyncDefault[I, P, T]: ...

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

    __weakself__: weakref.ref[I]
    __wrapped__: AnyFn[Concatenate[I, P], T]
    def __init__(
        self,
        instance: I,
        unbound: AnyFn[Concatenate[I, P], T],
        async_def: bool,
        **modifiers: Unpack[ModifierKwargs]
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

    @overload
    def __call__(self, *args: P.args, sync: Literal[True], **kwargs: P.kwargs) -> T: ...
    @overload
    def __call__(
        self, *args: P.args, sync: Literal[False], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]: ...
    @overload
    def __call__(self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs) -> T: ...
    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[True], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]: ...
    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MaybeCoro[T]: ...
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

    @functools.cached_property
    def __bound_to_a_sync_instance__(self) -> bool:
        """
        Check if the method is bound to an ASyncABC instance.

        Examples:
            >>> bound_method = ASyncBoundMethod(instance, my_function, True)
            >>> bound_method.__bound_to_a_sync_instance__
            True
        """

    def map(
        self,
        *iterables: AnyIterable[I],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **kwargs: P.kwargs
    ) -> TaskMapping[I, T]:
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

    async def any(
        self,
        *iterables: AnyIterable[I],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **kwargs: P.kwargs
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

    async def all(
        self,
        *iterables: AnyIterable[I],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **kwargs: P.kwargs
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

    async def min(
        self,
        *iterables: AnyIterable[I],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **kwargs: P.kwargs
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

    async def max(
        self,
        *iterables: AnyIterable[I],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **kwargs: P.kwargs
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

    async def sum(
        self,
        *iterables: AnyIterable[I],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **kwargs: P.kwargs
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
    def __call__(self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs) -> T: ...
    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[True], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]: ...
    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T: ...
    __call__: Incomplete

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
    def __call__(self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs) -> T: ...
    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[True], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]: ...
    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Coroutine[Any, Any, T]: ...
    __call__: Incomplete
