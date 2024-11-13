"""
This module contains the ASyncDescriptor class, which is used to create sync/async methods
and properties.

It also includes utility methods for mapping operations across multiple instances.
"""

import functools

from a_sync._typing import *
from a_sync.a_sync import decorator
from a_sync.a_sync.function import ASyncFunction, ModifierManager, _ModifiedMixin

if TYPE_CHECKING:
    from a_sync import TaskMapping


class ASyncDescriptor(_ModifiedMixin, Generic[I, P, T]):
    """
    A descriptor base class for dual-function ASync methods and properties.

    This class provides functionality for mapping operations across multiple instances
    and includes utility methods for common operations such as checking if all or any
    results are truthy, and finding the minimum, maximum, or sum of results of the method
    or property mapped across multiple instances.
    """

    __wrapped__: AnyFn[Concatenate[I, P], T]
    """The wrapped function or method."""

    __slots__ = "field_name", "_fget"

    def __init__(
        self,
        _fget: AnyFn[Concatenate[I, P], T],
        field_name: Optional[str] = None,
        **modifiers: ModifierKwargs,
    ) -> None:
        """
        Initialize the {cls}.

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
        if isinstance(_fget, ASyncFunction):
            self.modifiers.update(_fget.modifiers)
            self.__wrapped__ = _fget
        elif asyncio.iscoroutinefunction(_fget):
            self.__wrapped__: AsyncUnboundMethod[I, P, T] = (
                self.modifiers.apply_async_modifiers(_fget)
            )
        else:
            self.__wrapped__ = _fget

        self.field_name = field_name or _fget.__name__
        """The name of the field the {cls} is bound to."""

        functools.update_wrapper(self, self.__wrapped__)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} for {self.__wrapped__}>"

    def __set_name__(self, owner, name):
        """
        Set the field name when the {cls} is assigned to a class.

        Args:
            owner: The class owning this descriptor.
            name: The name assigned to this descriptor in the class.
        """
        self.field_name = name

    def map(
        self, *instances: AnyIterable[I], **bound_method_kwargs: P.kwargs
    ) -> "TaskMapping[I, T]":
        """
        Create a TaskMapping for the given instances.

        Args:
            *instances: Iterable of instances to map over.
            **bound_method_kwargs: Additional keyword arguments for the bound method.

        Returns:
            A TaskMapping object.
        """
        from a_sync.task import TaskMapping

        return TaskMapping(self, *instances, **bound_method_kwargs)

    @functools.cached_property
    def all(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], bool]:
        """
        Create an :class:`~ASyncFunction` that checks if all results are truthy.

        Returns:
            An ASyncFunction object.
        """
        return decorator.a_sync(default=self.default)(self._all)

    @functools.cached_property
    def any(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], bool]:
        """
        Create an :class:`~ASyncFunction` that checks if any result is truthy.

        Returns:
            An ASyncFunction object.
        """
        return decorator.a_sync(default=self.default)(self._any)

    @functools.cached_property
    def min(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], T]:
        """
        Create an :class:`~ASyncFunction` that returns the minimum result.

        Returns:
            An ASyncFunction object.
        """
        return decorator.a_sync(default=self.default)(self._min)

    @functools.cached_property
    def max(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], T]:
        """
        Create an :class:`~ASyncFunction` that returns the maximum result.

        Returns:
            An ASyncFunction object.
        """
        return decorator.a_sync(default=self.default)(self._max)

    @functools.cached_property
    def sum(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], T]:
        """
        Create an :class:`~ASyncFunction` that returns the sum of results.

        Returns:
            An ASyncFunction object.
        """
        return decorator.a_sync(default=self.default)(self._sum)

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

        Returns:
            A boolean indicating if all results are truthy.
        """
        return await self.map(
            *instances, concurrency=concurrency, name=name, **kwargs
        ).all(pop=True, sync=False)

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

        Returns:
            A boolean indicating if any result is truthy.
        """
        return await self.map(
            *instances, concurrency=concurrency, name=name, **kwargs
        ).any(pop=True, sync=False)

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

        Returns:
            The minimum result.
        """
        return await self.map(
            *instances, concurrency=concurrency, name=name, **kwargs
        ).min(pop=True, sync=False)

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

        Returns:
            The maximum result.
        """
        return await self.map(
            *instances, concurrency=concurrency, name=name, **kwargs
        ).max(pop=True, sync=False)

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

        Returns:
            The sum of the results.
        """
        return await self.map(
            *instances, concurrency=concurrency, name=name, **kwargs
        ).sum(pop=True, sync=False)

    def __init_subclass__(cls) -> None:
        for attr in cls.__dict__.values():
            if attr.__doc__ and "{cls}" in attr.__doc__:
                attr.__doc__ = attr.__doc__.replace("{cls}", f":class:`{cls.__name__}`")
        return super().__init_subclass__()
