"""
This module contains the :class:`ASyncDescriptor` class, which is used to create dual-function sync/async methods
and properties.

The :class:`ASyncDescriptor` class provides a base for creating descriptors that can handle both synchronous and asynchronous
operations. It includes utility methods for mapping operations across multiple instances and provides access to common
operations such as checking if all or any results are truthy, and finding the minimum, maximum, or sum of results of the
method or property mapped across multiple instances through the use of :class:`~a_sync.a_sync.function.ASyncFunction`.

See Also:
    - :class:`~a_sync.a_sync.function.ASyncFunction`
    - :class:`~a_sync.a_sync.method.ASyncMethodDescriptor`
    - :class:`~a_sync.a_sync.property.ASyncPropertyDescriptor`
"""

import asyncio

from a_sync._typing import *
from a_sync.a_sync import decorator, function
#from a_sync.a_sync.function import ASyncFunction
from a_sync.a_sync.function cimport _ModifiedMixin, _validate_wrapped_fn
from a_sync.a_sync.modifiers.manager cimport ModifierManager
from a_sync.functools cimport cached_property_unsafe, update_wrapper

if TYPE_CHECKING:
    from a_sync import TaskMapping


# cdef asyncio
cdef object iscoroutinefunction = asyncio.iscoroutinefunction
del asyncio

cdef object a_sync = decorator.a_sync
cdef object ASyncFunction = function.ASyncFunction


class ASyncDescriptor(_ModifiedMixin, Generic[I, P, T]):
    """
    A descriptor base class for dual-function ASync methods and properties.

    This class provides functionality for mapping operations across multiple instances
    and includes utility methods for common operations such as checking if all or any
    results are truthy, and finding the minimum, maximum, or sum of results of the method
    or property mapped across multiple instances through the use of :class:`~a_sync.a_sync.function.ASyncFunction`.

    Examples:
        To create a dual-function method or property, subclass :class:`ASyncDescriptor` and implement
        the desired functionality. You can then use the provided utility methods to perform operations
        across multiple instances.

        ```python
        class MyClass:
            @ASyncDescriptor
            def my_method(self, x):
                return x * 2

        instance = MyClass()
        result = instance.my_method.map([1, 2, 3])
        ```

    See Also:
        - :class:`~a_sync.a_sync.function.ASyncFunction`
        - :class:`~a_sync.a_sync.method.ASyncMethodDescriptor`
    """

    __slots__ = "field_name", "_fget"

    def __init__(
        _ModifiedMixin self,
        _fget: AnyFn[Concatenate[I, P], T],
        field_name: Optional[str] = None,
        **modifiers: ModifierKwargs,
    ) -> None:
        """
        Initialize the :class:`ASyncDescriptor`.

        Args:
            _fget: The function to be wrapped.
            field_name: Optional name for the field. If not provided, the function's name will be used.
            **modifiers: Additional modifier arguments.

        Raises:
            ValueError: If _fget is not callable.
        """
        if not callable(_fget):
            raise ValueError(f"Unable to decorate {_fget}")
        self.modifiers = ModifierManager(modifiers)
        if isinstance(_fget, <object>ASyncFunction):
            self.modifiers._modifiers.update((<_ModifiedMixin>_fget).modifiers._modifiers)
            self.__wrapped__ = _fget
        elif iscoroutinefunction(_fget):
            _validate_wrapped_fn(_fget)
            self.__wrapped__: AsyncUnboundMethod[I, P, T] = self.modifiers.apply_async_modifiers(
                _fget
            )
        else:
            _validate_wrapped_fn(_fget)
            self.__wrapped__ = _fget

        self.field_name = field_name or _fget.__name__
        """The name of the field the :class:`ASyncDescriptor` is bound to."""

        update_wrapper(self, self.__wrapped__)

    def __repr__(_ModifiedMixin self) -> str:
        return f"<{self.__class__.__name__} for {self.__wrapped__}>"

    def __set_name__(self, owner, name):
        """
        Set the field name when the :class:`ASyncDescriptor` is assigned to a class.

        Args:
            owner: The class owning this descriptor.
            name: The name assigned to this descriptor in the class.
        """
        self.field_name = name

    def map(
        self, *instances: AnyIterable[I], **bound_method_kwargs: P.kwargs
    ) -> "TaskMapping[I, T]":
        """
        Create a :class:`TaskMapping` for the given instances.

        Args:
            *instances: Iterable of instances to map over.
            **bound_method_kwargs: Additional keyword arguments for the bound method.

        Returns:
            A :class:`TaskMapping` object.

        Examples:
            class MyClass:
                @ASyncDescriptor
                def my_method(self, x):
                    return x * 2

            instance = MyClass()
            result = instance.my_method.map([1, 2, 3])
        """
        from a_sync.task import TaskMapping

        return TaskMapping(self, *instances, **bound_method_kwargs)

    @cached_property_unsafe
    def all(self) -> "ASyncFunction[Concatenate[AnyIterable[I], P], bool]":
        """
        Create an :class:`~ASyncFunction` that checks if all results are truthy.

        Returns:
            An :class:`ASyncFunction` object.

        Examples:
            class MyClass:
                @ASyncDescriptor
                def my_method(self, x):
                    return x > 0

            instance = MyClass()
            result = await instance.my_method.all([1, 2, 3])
        """
        return a_sync(default=self.default)(self._all)

    @cached_property_unsafe
    def any(self) -> "ASyncFunction[Concatenate[AnyIterable[I], P], bool]":
        """
        Create an :class:`~ASyncFunction` that checks if any result is truthy.

        Returns:
            An :class:`ASyncFunction` object.

        Examples:
            class MyClass:
                @ASyncDescriptor
                def my_method(self, x):
                    return x > 0

            instance = MyClass()
            result = await instance.my_method.any([-1, 0, 1])
        """
        return a_sync(default=self.default)(self._any)

    @cached_property_unsafe
    def min(self) -> "ASyncFunction[Concatenate[AnyIterable[I], P], T]":
        """
        Create an :class:`~ASyncFunction` that returns the minimum result.

        Returns:
            An :class:`ASyncFunction` object.

        Examples:
            ```python
            class MyClass:
                @ASyncDescriptor
                def my_method(self, x):
                    return x

            instance = MyClass()
            result = await instance.my_method.min([3, 1, 2])
            ```
        """
        return a_sync(default=self.default)(self._min)

    @cached_property_unsafe
    def max(self) -> "ASyncFunction[Concatenate[AnyIterable[I], P], T]":
        """
        Create an :class:`~ASyncFunction` that returns the maximum result.

        Returns:
            An :class:`ASyncFunction` object.

        Examples:
            class MyClass:
                @ASyncDescriptor
                def my_method(self, x):
                    return x

            instance = MyClass()
            result = await instance.my_method.max([3, 1, 2])
        """
        return a_sync(default=self.default)(self._max)

    @cached_property_unsafe
    def sum(self) -> "ASyncFunction[Concatenate[AnyIterable[I], P], T]":
        """
        Create an :class:`~ASyncFunction` that returns the sum of results.

        Returns:
            An :class:`ASyncFunction` object.

        Examples:
            ```python
            class MyClass:
                @ASyncDescriptor
                def my_method(self, x):
                    return x

            instance = MyClass()
            result = await instance.my_method.sum([1, 2, 3])
            ```
        """
        return a_sync(default=self.default)(self._sum)

    async def _all(
        self,
        *instances: AnyIterable[I],
        concurrency: Optional[int] = None,
        name: str = "",
        **kwargs: P.kwargs,
    ) -> bool:
        """
        Check if all results are truthy.

        Args:
            *instances: Iterable of instances to check.
            concurrency: Optional maximum number of concurrent tasks.
            name: Optional name for the task.
            **kwargs: Additional keyword arguments.

        Examples:
            ```python
            class MyClass:
                @ASyncDescriptor
                def my_method(self, x):
                    return x > 0

            instance = MyClass()
            result = await instance.my_method._all([1, 2, 3])
            ```
        """
        return await self.map(*instances, concurrency=concurrency, name=name, **kwargs).all(
            pop=True, sync=False
        )

    async def _any(
        self,
        *instances: AnyIterable[I],
        concurrency: Optional[int] = None,
        name: str = "",
        **kwargs: P.kwargs,
    ) -> bool:
        """
        Check if any result is truthy.

        Args:
            *instances: Iterable of instances to check.
            concurrency: Optional maximum number of concurrent tasks.
            name: Optional name for the task.
            **kwargs: Additional keyword arguments.

        Examples:
            ```python
            class MyClass:
                @ASyncDescriptor
                def my_method(self, x):
                    return x > 0

            instance = MyClass()
            result = await instance.my_method._any([-1, 0, 1])
            ```
        """
        return await self.map(*instances, concurrency=concurrency, name=name, **kwargs).any(
            pop=True, sync=False
        )

    async def _min(
        self,
        *instances: AnyIterable[I],
        concurrency: Optional[int] = None,
        name: str = "",
        **kwargs: P.kwargs,
    ) -> T:
        """
        Find the minimum result.

        Args:
            *instances: Iterable of instances to check.
            concurrency: Optional maximum number of concurrent tasks.
            name: Optional name for the task.
            **kwargs: Additional keyword arguments.

        Examples:
            ```python
            class MyClass:
                @ASyncDescriptor
                def my_method(self, x):
                    return x

            instance = MyClass()
            result = await instance.my_method._min([3, 1, 2])
            ```
        """
        return await self.map(*instances, concurrency=concurrency, name=name, **kwargs).min(
            pop=True, sync=False
        )

    async def _max(
        self,
        *instances: AnyIterable[I],
        concurrency: Optional[int] = None,
        name: str = "",
        **kwargs: P.kwargs,
    ) -> T:
        """
        Find the maximum result.

        Args:
            *instances: Iterable of instances to check.
            concurrency: Optional maximum number of concurrent tasks.
            name: Optional name for the task.
            **kwargs: Additional keyword arguments.

        Examples:
            ```python
            class MyClass:
                @ASyncDescriptor
                def my_method(self, x):
                    return x

            instance = MyClass()
            result = await instance.my_method._max([3, 1, 2])
            ```
        """
        return await self.map(*instances, concurrency=concurrency, name=name, **kwargs).max(
            pop=True, sync=False
        )

    async def _sum(
        self,
        *instances: AnyIterable[I],
        concurrency: Optional[int] = None,
        name: str = "",
        **kwargs: P.kwargs,
    ) -> T:
        """
        Calculate the sum of results.

        Args:
            *instances: Iterable of instances to sum.
            concurrency: Optional maximum number of concurrent tasks.
            name: Optional name for the task.
            **kwargs: Additional keyword arguments.

        Examples:
            ```python
            class MyClass:
                @ASyncDescriptor
                def my_method(self, x):
                    return x

            instance = MyClass()
            result = await instance.my_method._sum([1, 2, 3])
            ```
        """
        return await self.map(*instances, concurrency=concurrency, name=name, **kwargs).sum(
            pop=True, sync=False
        )

    def __init_subclass__(cls) -> None:
        for attr in cls.__dict__.values():
            if attr.__doc__ and "{cls}" in attr.__doc__:
                attr.__doc__ = attr.__doc__.replace("{cls}", f":class:`{cls.__name__}`")
        return super().__init_subclass__()
