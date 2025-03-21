# type: ignore [var-annotated]

"""
The `future.py` module provides functionality for handling asynchronous futures,
including a decorator for converting callables into `ASyncFuture` objects and
utilities for managing asynchronous computations.

Functions:
    future(callable: Union[Callable[P, Awaitable[T]], Callable[P, T]] = None, **kwargs: Unpack[ModifierKwargs]) -> Callable[P, Union[T, "ASyncFuture[T]"]]:
        A decorator to convert a callable into an `ASyncFuture`, with optional modifiers.
    _gather_check_and_materialize(*things: Unpack[MaybeAwaitable[T]]) -> List[T]:
        Gathers and materializes a list of awaitable or non-awaitable items.
    _check_and_materialize(thing: T) -> T:
        Checks if an item is awaitable and materializes it.
    _materialize(meta: "ASyncFuture[T]") -> T:
        Materializes the result of an `ASyncFuture`.

Classes:
    ASyncFuture: Represents an asynchronous future result.

TODO include a simple mathematics example a one complex example with numerous variables and operations
TODO include attribute access examples
TODO describe a bit more about both of the above 2 TODOs somewhere in this module-level docstring
TODO describe why a user would want to use these (to write cleaner code that doesn't require as many ugly gathers)
TODO include comparisons between the 'new way' with this future class and the 'old way' with gathers
"""

import concurrent.futures
from asyncio import Future, Task, get_event_loop
from functools import partial, wraps
from inspect import isawaitable

from a_sync._typing import *
from a_sync.asyncio import create_task, igather


def future(
    callable: AnyFn[P, T] = None,
    **kwargs: Unpack[ModifierKwargs],
) -> Callable[P, Union[T, "ASyncFuture[T]"]]:
    """
    A decorator function to convert a callable into an `ASyncFuture`, with optional modifiers.

    This function wraps the provided callable in an `_ASyncFutureWrappedFn` instance,
    which returns an `ASyncFuture` when called. The `ASyncFuture` allows the result
    of the callable to be awaited or accessed synchronously.

    Args:
        callable: The callable to convert. Defaults to None.
        **kwargs: Additional keyword arguments for the modifier.

    Returns:
        A callable that returns either the result or an `ASyncFuture`.

    Example:
        >>> @future
        ... async def async_function():
        ...     return 42
        >>> result = async_function()
        >>> isinstance(result, ASyncFuture)
        True

    See Also:
        :class:`ASyncFuture`
    """
    return _ASyncFutureWrappedFn(callable, **kwargs)


async def _gather_check_and_materialize(*things: Unpack[MaybeAwaitable[T]]) -> List[T]:
    """
    Gathers and materializes a list of awaitable or non-awaitable items.

    This function takes a list of items that may be awaitable or not, and
    returns a list of their results. Awaitable items are awaited, while
    non-awaitable items are returned as-is.

    Args:
        *things: Items to gather and materialize.

    Example:
        >>> async def async_fn(x):
        ...     return x
        >>> await _gather_check_and_materialize(async_fn(1), 2, async_fn(3))
        [1, 2, 3]
    """
    return await igather(map(_check_and_materialize, things))


async def _check_and_materialize(thing: T) -> T:
    """
    Checks if an item is awaitable and materializes it.

    If the item is awaitable, it is awaited and the result is returned.
    Otherwise, the item is returned as-is.

    Args:
        thing: The item to check and materialize.

    Example:
        >>> async def async_fn():
        ...     return 42
        >>> await _check_and_materialize(async_fn())
        42
    """
    return await thing if isawaitable(thing) else thing


def _materialize(meta: "ASyncFuture[T]") -> T:
    """
    Materializes the result of an `ASyncFuture`.

    This function attempts to run the event loop until the `ASyncFuture` is complete.
    If the event loop is already running, it raises a RuntimeError.

    Args:
        meta: The `ASyncFuture` to materialize.

    Raises:
        RuntimeError: If the event loop is running and the result cannot be awaited.

    Example:
        >>> future = ASyncFuture(asyncio.sleep(1, result=42))
        >>> _materialize(future)
        42

    See Also:
        :class:`ASyncFuture`
    """
    try:
        return get_event_loop().run_until_complete(meta)
    except RuntimeError as e:
        raise RuntimeError(
            f"{meta} result is not set and the event loop is running, you will need to await it first"
        ) from e


MetaNumeric = Union[Numeric, "ASyncFuture[int]", "ASyncFuture[float]", "ASyncFuture[Decimal]"]

_cf_init = concurrent.futures.Future.__init__
_cf_result = concurrent.futures.Future.result


@final
class ASyncFuture(concurrent.futures.Future, Awaitable[T]):
    """
    A class representing an asynchronous future result.

    Inherits from both `concurrent.futures.Future` and `Awaitable[T]`, allowing it to be used in both synchronous and asynchronous contexts.

    The `ASyncFuture` class provides additional functionality for arithmetic operations,
    comparisons, and conversions, making it versatile for various use cases.

    Example:
        >>> async def async_fn():
        ...     return 42
        >>> future = ASyncFuture(async_fn())
        >>> await future
        42

    Note:
        Arithmetic operations are implemented, allowing for mathematical operations on future results.
        You no longer have to choose between optimized async code and clean, readable code.

    Example:
        >>> future1 = ASyncFuture(asyncio.sleep(1, result=10))
        >>> future2 = ASyncFuture(asyncio.sleep(1, result=5))
        >>> future3 = ASyncFuture(asyncio.sleep(1, result=10))
        >>> future4 = ASyncFuture(asyncio.sleep(1, result=2))
        >>> result = (future1 + future2) / future3 ** future4
        >>> await result
        0.15

    Attribute Access:
        The `ASyncFuture` allows attribute access on the materialized result.

    Example:
        >>> class Example:
        ...     def __init__(self, value):
        ...         self.value = value
        >>> future = ASyncFuture(asyncio.sleep(1, result=Example(42)))
        >>> future.value
        42

    See Also:
        :func:`future` for creating `ASyncFuture` instances.
    """

    __slots__ = "__awaitable__", "__dependencies", "__dependants", "__task"

    def __init__(
        self, awaitable: Awaitable[T], dependencies: List["ASyncFuture"] = []
    ) -> None:  # sourcery skip: default-mutable-arg
        """
        Initializes an `ASyncFuture` with an awaitable and optional dependencies.

        Args:
            awaitable: The awaitable object.
            dependencies: A list of dependencies. Defaults to [].

        Example:
            >>> async def async_fn():
            ...     return 42
            >>> future = ASyncFuture(async_fn())
            >>> await future
            42
        """

        self.__awaitable__ = awaitable
        """The awaitable object."""

        self.__dependencies = dependencies
        """A list of dependencies."""

        for dependency in dependencies:
            assert isinstance(dependency, ASyncFuture)
            dependency.__dependants.append(self)

        self.__dependants: List[ASyncFuture] = []
        """A list of dependants."""

        self.__task = None
        """The task associated with the awaitable."""

        _cf_init(self)

    def __hash__(self) -> int:
        return hash(self.__awaitable__)

    def __repr__(self) -> str:
        string = f"<{self.__class__.__name__} {self._state} for {self.__awaitable__}"
        if self.cancelled():
            pass
        elif self.done():
            string += (
                f" exception={self.exception()}"
                if self.exception()
                else f" result={_cf_result(self)}"
            )
        return f"{string}>"

    def __list_dependencies(self, other) -> List["ASyncFuture"]:
        """
        Lists dependencies for the `ASyncFuture`.

        Args:
            other: The other dependency to list.

        Returns:
            A list of dependencies including the current and other `ASyncFuture`.
        """
        return [self, other] if isinstance(other, ASyncFuture) else [self]

    @property
    def result(self) -> Union[Callable[[], T], Any]:
        # sourcery skip: assign-if-exp, reintroduce-else
        """
        If this future is not done, it will work like `cf.Future.result`. It will block, await the awaitable, and return the result when ready.
        If this future is done and the result has attribute `result`, will return `getattr(future_result, 'result')`
        If this future is done and the result does NOT have attribute `result`, will again work like `cf.Future.result`

        Example:
            >>> future = ASyncFuture(asyncio.sleep(1, result=42))
            >>> future.result()
            42
        """
        if self.done():
            if hasattr(r := _cf_result(self), "result"):
                # can be property, method, whatever. should work.
                return r.result
            # the result should be callable like an asyncio.Future
            return lambda: _cf_result(self)
        return lambda: _materialize(self)

    def __getattr__(self, attr: str) -> Any:
        """
        Allows access to attributes of the materialized result.

        Args:
            attr: The attribute name to access.

        Returns:
            The attribute value from the materialized result.

        Example:
            >>> class Example:
            ...     def __init__(self, value):
            ...         self.value = value
            >>> future = ASyncFuture(asyncio.sleep(1, result=Example(42)))
            >>> future.value
            42
        """
        return getattr(_materialize(self), attr)

    def __getitem__(self, key) -> Any:
        """
        Allows item access on the materialized result.

        Args:
            key: The key to access.

        Returns:
            The item from the materialized result.

        Example:
            >>> future = ASyncFuture(asyncio.sleep(1, result={'key': 'value'}))
            >>> future['key']
            'value'
        """
        return _materialize(self)[key]

    # NOTE: broken, do not use. I think
    def __setitem__(self, key, value) -> None:
        """
        Allows setting an item on the materialized result.

        Args:
            key: The key to set.
            value: The value to set.

        Example:
            >>> future = ASyncFuture(asyncio.sleep(1, result={'key': 'value'}))
            >>> future['key'] = 'new_value'
        """
        _materialize(self)[key] = value

    # not sure what to call these
    def __contains__(self, key: Any) -> bool:
        """
        Checks if a key is in the materialized result.

        Args:
            key: The key to check.

        Returns:
            True if the key is in the materialized result, False otherwise.

        Example:
            >>> future = ASyncFuture(asyncio.sleep(1, result={'key': 'value'}))
            >>> 'key' in future
            True
        """
        return _materialize(
            ASyncFuture(self.__contains(key), dependencies=self.__list_dependencies(key))
        )

    def __await__(self) -> Generator[Any, None, T]:
        """
        Makes the `ASyncFuture` awaitable.

        Example:
            >>> future = ASyncFuture(asyncio.sleep(1, result=42))
            >>> await future
            42
        """
        return self.__await().__await__()

    async def __await(self) -> T:
        if not self.done():
            self.set_result(await self.__task__)
        return self._result

    @property
    def __task__(self) -> "Task[T]":
        """
        Returns the asyncio task associated with the awaitable, creating it if necessary.

        Example:
            >>> future = ASyncFuture(asyncio.sleep(1, result=42))
            >>> task = future.__task__
            >>> isinstance(task, asyncio.Task)
            True
        """
        if self.__task is None:
            self.__task = create_task(self.__awaitable__)
        return self.__task

    def __iter__(self):
        """
        Returns an iterator for the materialized result.

        Example:
            >>> future = ASyncFuture(asyncio.sleep(1, result=[1, 2, 3]))
            >>> for item in future:
            ...     print(item)
            1
            2
            3
        """
        return _materialize(self).__iter__()

    def __next__(self):
        """
        Returns the next item from the materialized result.

        Example:
            >>> future = ASyncFuture(asyncio.sleep(1, result=iter([1, 2, 3])))
            >>> next(future)
            1
        """
        return _materialize(self).__next__()

    def __enter__(self):
        """
        Enters the context of the materialized result.

        Example:
            >>> class SomeContext:
            ...     def __enter__(self):
            ...         return self
            ...     def __exit__(self, exc_type, exc_val, exc_tb):
            ...         pass
            >>> future = ASyncFuture(asyncio.sleep(1, result=SomeContext()))
            >>> with future as context:
            ...     context.do_something()
        """
        return _materialize(self).__enter__()

    def __exit__(self, *args):
        """
        Exits the context of the materialized result.

        Example:
            >>> class SomeContext:
            ...     def __enter__(self):
            ...         return self
            ...     def __exit__(self, exc_type, exc_val, exc_tb):
            ...         pass
            >>> future = ASyncFuture(asyncio.sleep(1, result=SomeContext()))
            >>> with future as context:
            ...     pass
            >>> # Context is exited here
        """
        return _materialize(self).__exit__(*args)

    @overload
    def __add__(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]": ...

    @overload
    def __add__(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]": ...

    @overload
    def __add__(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]": ...

    @overload
    def __add__(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]": ...

    @overload
    def __add__(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    def __add__(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]": ...

    @overload
    def __add__(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    def __add__(self: "ASyncFuture[int]", other: Awaitable[int]) -> "ASyncFuture[int]": ...

    @overload
    def __add__(self: "ASyncFuture[float]", other: Awaitable[float]) -> "ASyncFuture[float]": ...

    @overload
    def __add__(self: "ASyncFuture[float]", other: Awaitable[int]) -> "ASyncFuture[float]": ...

    @overload
    def __add__(self: "ASyncFuture[int]", other: Awaitable[float]) -> "ASyncFuture[float]": ...

    @overload
    def __add__(
        self: "ASyncFuture[Decimal]", other: Awaitable[Decimal]
    ) -> "ASyncFuture[Decimal]": ...

    @overload
    def __add__(self: "ASyncFuture[Decimal]", other: Awaitable[int]) -> "ASyncFuture[Decimal]": ...

    @overload
    def __add__(self: "ASyncFuture[int]", other: Awaitable[Decimal]) -> "ASyncFuture[Decimal]": ...

    def __add__(self, other: MetaNumeric) -> "ASyncFuture":
        """
        Adds the result of this `ASyncFuture` to another value or `ASyncFuture`.

        Args:
            other: The value or `ASyncFuture` to add.

        Returns:
            A new `ASyncFuture` representing the sum.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=5))
            >>> result = future1 + future2
            >>> await result
            15
        """
        return ASyncFuture(self.__add(other), dependencies=self.__list_dependencies(other))

    @overload
    def __sub__(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]": ...

    @overload
    def __sub__(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]": ...

    @overload
    def __sub__(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]": ...

    @overload
    def __sub__(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]": ...

    @overload
    def __sub__(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    def __sub__(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]": ...

    @overload
    def __sub__(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    def __sub__(self: "ASyncFuture[int]", other: Awaitable[int]) -> "ASyncFuture[int]": ...

    @overload
    def __sub__(self: "ASyncFuture[float]", other: Awaitable[float]) -> "ASyncFuture[float]": ...

    @overload
    def __sub__(self: "ASyncFuture[float]", other: Awaitable[int]) -> "ASyncFuture[float]": ...

    @overload
    def __sub__(self: "ASyncFuture[int]", other: Awaitable[float]) -> "ASyncFuture[float]": ...

    @overload
    def __sub__(
        self: "ASyncFuture[Decimal]", other: Awaitable[Decimal]
    ) -> "ASyncFuture[Decimal]": ...

    @overload
    def __sub__(self: "ASyncFuture[Decimal]", other: Awaitable[int]) -> "ASyncFuture[Decimal]": ...

    @overload
    def __sub__(self: "ASyncFuture[int]", other: Awaitable[Decimal]) -> "ASyncFuture[Decimal]": ...

    def __sub__(self, other: MetaNumeric) -> "ASyncFuture":
        """
        Subtracts another value or `ASyncFuture` from the result of this `ASyncFuture`.

        Args:
            other: The value or `ASyncFuture` to subtract.

        Returns:
            A new `ASyncFuture` representing the difference.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=5))
            >>> result = future1 - future2
            >>> await result
            5
        """
        return ASyncFuture(self.__sub(other), dependencies=self.__list_dependencies(other))

    def __mul__(self, other) -> "ASyncFuture":
        """
        Multiplies the result of this `ASyncFuture` by another value or `ASyncFuture`.

        Args:
            other: The value or `ASyncFuture` to multiply.

        Returns:
            A new `ASyncFuture` representing the product.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=5))
            >>> result = future1 * future2
            >>> await result
            50
        """
        return ASyncFuture(self.__mul(other), dependencies=self.__list_dependencies(other))

    def __pow__(self, other) -> "ASyncFuture":
        """
        Raises the result of this `ASyncFuture` to the power of another value or `ASyncFuture`.

        Args:
            other: The exponent value or `ASyncFuture`.

        Returns:
            A new `ASyncFuture` representing the power.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=2))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=3))
            >>> result = future1 ** future2
            >>> await result
            8
        """
        return ASyncFuture(self.__pow(other), dependencies=self.__list_dependencies(other))

    def __truediv__(self, other) -> "ASyncFuture":
        """
        Divides the result of this `ASyncFuture` by another value or `ASyncFuture`.

        Args:
            other: The divisor value or `ASyncFuture`.

        Returns:
            A new `ASyncFuture` representing the quotient.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=2))
            >>> result = future1 / future2
            >>> await result
            5.0
        """
        return ASyncFuture(self.__truediv(other), dependencies=self.__list_dependencies(other))

    def __floordiv__(self, other) -> "ASyncFuture":
        """
        Performs floor division of the result of this `ASyncFuture` by another value or `ASyncFuture`.

        Args:
            other: The divisor value or `ASyncFuture`.

        Returns:
            A new `ASyncFuture` representing the floor division result.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=3))
            >>> result = future1 // future2
            >>> await result
            3
        """
        return ASyncFuture(self.__floordiv(other), dependencies=self.__list_dependencies(other))

    def __pow__(self, other) -> "ASyncFuture":
        """
        Raises the result of this `ASyncFuture` to the power of another value or `ASyncFuture`.

        Args:
            other: The exponent value or `ASyncFuture`.

        Returns:
            A new `ASyncFuture` representing the power.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=2))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=3))
            >>> result = future1 ** future2
            >>> await result
            8
        """
        return ASyncFuture(self.__pow(other), dependencies=self.__list_dependencies(other))

    @overload
    def __radd__(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]": ...

    @overload
    def __radd__(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]": ...

    @overload
    def __radd__(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]": ...

    @overload
    def __radd__(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]": ...

    @overload
    def __radd__(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    def __radd__(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]": ...

    @overload
    def __radd__(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    def __radd__(self: "ASyncFuture[int]", other: Awaitable[int]) -> "ASyncFuture[int]": ...

    @overload
    def __radd__(self: "ASyncFuture[float]", other: Awaitable[float]) -> "ASyncFuture[float]": ...

    @overload
    def __radd__(self: "ASyncFuture[float]", other: Awaitable[int]) -> "ASyncFuture[float]": ...

    @overload
    def __radd__(self: "ASyncFuture[int]", other: Awaitable[float]) -> "ASyncFuture[float]": ...

    @overload
    def __radd__(
        self: "ASyncFuture[Decimal]", other: Awaitable[Decimal]
    ) -> "ASyncFuture[Decimal]": ...

    @overload
    def __radd__(self: "ASyncFuture[Decimal]", other: Awaitable[int]) -> "ASyncFuture[Decimal]": ...

    @overload
    def __radd__(self: "ASyncFuture[int]", other: Awaitable[Decimal]) -> "ASyncFuture[Decimal]": ...

    def __radd__(self, other) -> "ASyncFuture":
        """
        Adds another value or `ASyncFuture` to the result of this `ASyncFuture`.

        Args:
            other: The value or `ASyncFuture` to add.

        Returns:
            A new `ASyncFuture` representing the sum.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> result = 5 + future1
            >>> await result
            15
        """
        return ASyncFuture(self.__radd(other), dependencies=self.__list_dependencies(other))

    @overload
    def __rsub__(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]": ...

    @overload
    def __rsub__(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]": ...

    @overload
    def __rsub__(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]": ...

    @overload
    def __rsub__(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]": ...

    @overload
    def __rsub__(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    def __rsub__(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]": ...

    @overload
    def __rsub__(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    def __rsub__(self: "ASyncFuture[int]", other: Awaitable[int]) -> "ASyncFuture[int]": ...

    @overload
    def __rsub__(self: "ASyncFuture[float]", other: Awaitable[float]) -> "ASyncFuture[float]": ...

    @overload
    def __rsub__(self: "ASyncFuture[float]", other: Awaitable[int]) -> "ASyncFuture[float]": ...

    @overload
    def __rsub__(self: "ASyncFuture[int]", other: Awaitable[float]) -> "ASyncFuture[float]": ...

    @overload
    def __rsub__(
        self: "ASyncFuture[Decimal]", other: Awaitable[Decimal]
    ) -> "ASyncFuture[Decimal]": ...

    @overload
    def __rsub__(self: "ASyncFuture[Decimal]", other: Awaitable[int]) -> "ASyncFuture[Decimal]": ...

    @overload
    def __rsub__(self: "ASyncFuture[int]", other: Awaitable[Decimal]) -> "ASyncFuture[Decimal]": ...

    def __rsub__(self, other) -> "ASyncFuture":
        """
        Subtracts the result of this `ASyncFuture` from another value or `ASyncFuture`.

        Args:
            other: The value or `ASyncFuture` to subtract from.

        Returns:
            A new `ASyncFuture` representing the difference.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> result = 20 - future1
            >>> await result
            10
        """
        return ASyncFuture(self.__rsub(other), dependencies=self.__list_dependencies(other))

    def __rmul__(self, other) -> "ASyncFuture":
        """
        Multiplies another value or `ASyncFuture` by the result of this `ASyncFuture`.

        Args:
            other: The value or `ASyncFuture` to multiply.

        Returns:
            A new `ASyncFuture` representing the product.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> result = 2 * future1
            >>> await result
            20
        """
        return ASyncFuture(self.__rmul(other), dependencies=self.__list_dependencies(other))

    def __rtruediv__(self, other) -> "ASyncFuture":
        """
        Divides another value or `ASyncFuture` by the result of this `ASyncFuture`.

        Args:
            other: The value or `ASyncFuture` to divide.

        Returns:
            A new `ASyncFuture` representing the quotient.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=2))
            >>> result = 10 / future1
            >>> await result
            5.0
        """
        return ASyncFuture(self.__rtruediv(other), dependencies=self.__list_dependencies(other))

    def __rfloordiv__(self, other) -> "ASyncFuture":
        """
        Performs floor division of another value or `ASyncFuture` by the result of this `ASyncFuture`.

        Args:
            other: The value or `ASyncFuture` to divide.

        Returns:
            A new `ASyncFuture` representing the floor division result.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=3))
            >>> result = 10 // future1
            >>> await result
            3
        """
        return ASyncFuture(self.__rfloordiv(other), dependencies=self.__list_dependencies(other))

    def __rpow__(self, other) -> "ASyncFuture":
        """
        Raises another value or `ASyncFuture` to the power of the result of this `ASyncFuture`.

        Args:
            other: The base value or `ASyncFuture`.

        Returns:
            A new `ASyncFuture` representing the power.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=3))
            >>> result = 2 ** future1
            >>> await result
            8
        """
        return ASyncFuture(self.__rpow(other), dependencies=self.__list_dependencies(other))

    def __eq__(self, other) -> "ASyncFuture":
        """
        Compares the result of this `ASyncFuture` with another value or `ASyncFuture` for equality.

        Args:
            other: The value or `ASyncFuture` to compare.

        Returns:
            A new `ASyncFuture` representing the equality comparison result.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> result = future1 == future2
            >>> await result
            True
        """
        return bool(ASyncFuture(self.__eq(other), dependencies=self.__list_dependencies(other)))

    def __gt__(self, other) -> "ASyncFuture":
        """
        Compares the result of this `ASyncFuture` with another value or `ASyncFuture` for greater than.

        Args:
            other: The value or `ASyncFuture` to compare.

        Returns:
            A new `ASyncFuture` representing the greater than comparison result.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=5))
            >>> result = future1 > future2
            >>> await result
            True
        """
        return ASyncFuture(self.__gt(other), dependencies=self.__list_dependencies(other))

    def __ge__(self, other) -> "ASyncFuture":
        """
        Compares the result of this `ASyncFuture` with another value or `ASyncFuture` for greater than or equal.

        Args:
            other: The value or `ASyncFuture` to compare.

        Returns:
            A new `ASyncFuture` representing the greater than or equal comparison result.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> result = future1 >= future2
            >>> await result
            True
        """
        return ASyncFuture(self.__ge(other), dependencies=self.__list_dependencies(other))

    def __lt__(self, other) -> "ASyncFuture":
        """
        Compares the result of this `ASyncFuture` with another value or `ASyncFuture` for less than.

        Args:
            other: The value or `ASyncFuture` to compare.

        Returns:
            A new `ASyncFuture` representing the less than comparison result.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=5))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=10))
            >>> result = future1 < future2
            >>> await result
            True
        """
        return ASyncFuture(self.__lt(other), dependencies=self.__list_dependencies(other))

    def __le__(self, other) -> "ASyncFuture":
        """
        Compares the result of this `ASyncFuture` with another value or `ASyncFuture` for less than or equal.

        Args:
            other: The value or `ASyncFuture` to compare.

        Returns:
            A new `ASyncFuture` representing the less than or equal comparison result.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=5))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=5))
            >>> result = future1 <= future2
            >>> await result
            True
        """
        return ASyncFuture(self.__le(other), dependencies=self.__list_dependencies(other))

    # Maths

    @overload
    async def __add(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]": ...

    @overload
    async def __add(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]": ...

    @overload
    async def __add(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]": ...

    @overload
    async def __add(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]": ...

    @overload
    async def __add(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __add(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __add(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __add(self: "ASyncFuture[int]", other: Awaitable[int]) -> "ASyncFuture[int]": ...

    @overload
    async def __add(
        self: "ASyncFuture[float]", other: Awaitable[float]
    ) -> "ASyncFuture[float]": ...

    @overload
    async def __add(self: "ASyncFuture[float]", other: Awaitable[int]) -> "ASyncFuture[float]": ...

    @overload
    async def __add(self: "ASyncFuture[int]", other: Awaitable[float]) -> "ASyncFuture[float]": ...

    @overload
    async def __add(
        self: "ASyncFuture[Decimal]", other: Awaitable[Decimal]
    ) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __add(
        self: "ASyncFuture[Decimal]", other: Awaitable[int]
    ) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __add(
        self: "ASyncFuture[int]", other: Awaitable[Decimal]
    ) -> "ASyncFuture[Decimal]": ...

    async def __add(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        return a + b

    @overload
    async def __sub(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]": ...

    @overload
    async def __sub(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]": ...

    @overload
    async def __sub(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]": ...

    @overload
    async def __sub(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]": ...

    @overload
    async def __sub(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __sub(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __sub(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __sub(self: "ASyncFuture[int]", other: Awaitable[int]) -> "ASyncFuture[int]": ...

    @overload
    async def __sub(
        self: "ASyncFuture[float]", other: Awaitable[float]
    ) -> "ASyncFuture[float]": ...

    @overload
    async def __sub(self: "ASyncFuture[float]", other: Awaitable[int]) -> "ASyncFuture[float]": ...

    @overload
    async def __sub(self: "ASyncFuture[int]", other: Awaitable[float]) -> "ASyncFuture[float]": ...

    @overload
    async def __sub(
        self: "ASyncFuture[Decimal]", other: Awaitable[Decimal]
    ) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __sub(
        self: "ASyncFuture[Decimal]", other: Awaitable[int]
    ) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __sub(
        self: "ASyncFuture[int]", other: Awaitable[Decimal]
    ) -> "ASyncFuture[Decimal]": ...

    async def __sub(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        return a - b

    async def __mul(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        return a * b

    async def __truediv(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        return a / b

    async def __floordiv(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        return a // b

    async def __pow(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        return a**b

    # rMaths
    @overload
    async def __radd(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]": ...

    @overload
    async def __radd(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]": ...

    @overload
    async def __radd(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]": ...

    @overload
    async def __radd(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]": ...

    @overload
    async def __radd(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __radd(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __radd(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __radd(self: "ASyncFuture[int]", other: Awaitable[int]) -> "ASyncFuture[int]": ...

    @overload
    async def __radd(
        self: "ASyncFuture[float]", other: Awaitable[float]
    ) -> "ASyncFuture[float]": ...

    @overload
    async def __radd(self: "ASyncFuture[float]", other: Awaitable[int]) -> "ASyncFuture[float]": ...

    @overload
    async def __radd(self: "ASyncFuture[int]", other: Awaitable[float]) -> "ASyncFuture[float]": ...

    @overload
    async def __radd(
        self: "ASyncFuture[Decimal]", other: Awaitable[Decimal]
    ) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __radd(
        self: "ASyncFuture[Decimal]", other: Awaitable[int]
    ) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __radd(
        self: "ASyncFuture[int]", other: Awaitable[Decimal]
    ) -> "ASyncFuture[Decimal]": ...

    async def __radd(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(other, self)
        return a + b

    @overload
    async def __rsub(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]": ...

    @overload
    async def __rsub(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]": ...

    @overload
    async def __rsub(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]": ...

    @overload
    async def __rsub(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]": ...

    @overload
    async def __rsub(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __rsub(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __rsub(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __rsub(self: "ASyncFuture[int]", other: Awaitable[int]) -> "ASyncFuture[int]": ...

    @overload
    async def __rsub(
        self: "ASyncFuture[float]", other: Awaitable[float]
    ) -> "ASyncFuture[float]": ...

    @overload
    async def __rsub(self: "ASyncFuture[float]", other: Awaitable[int]) -> "ASyncFuture[float]": ...

    @overload
    async def __rsub(self: "ASyncFuture[int]", other: Awaitable[float]) -> "ASyncFuture[float]": ...

    @overload
    async def __rsub(
        self: "ASyncFuture[Decimal]", other: Awaitable[Decimal]
    ) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __rsub(
        self: "ASyncFuture[Decimal]", other: Awaitable[int]
    ) -> "ASyncFuture[Decimal]": ...

    @overload
    async def __rsub(
        self: "ASyncFuture[int]", other: Awaitable[Decimal]
    ) -> "ASyncFuture[Decimal]": ...

    async def __rsub(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(other, self)
        return a - b

    async def __rmul(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(other, self)
        return a * b

    async def __rtruediv(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(other, self)
        return a / b

    async def __rfloordiv(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(other, self)
        return a // b

    async def __rpow(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(other, self)
        return a**b

    async def __iadd(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        self._result = a + b
        return self._result

    async def __isub(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        self._result = a - b
        return self._result

    async def __imul(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        self._result = a * b
        return self._result

    async def __itruediv(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        self._result = a / b
        return self._result

    async def __ifloordiv(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        self._result = a // b
        return self._result

    async def __ipow(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        self._result = a**b
        return self._result

    # Comparisons
    async def __eq(self, other) -> bool:
        a, b = await _gather_check_and_materialize(self, other)
        return a == b

    async def __gt(self, other) -> bool:
        a, b = await _gather_check_and_materialize(self, other)
        return a > b

    async def __ge(self, other) -> bool:
        a, b = await _gather_check_and_materialize(self, other)
        return a >= b

    async def __lt(self, other) -> bool:
        a, b = await _gather_check_and_materialize(self, other)
        return a < b

    async def __le(self, other) -> bool:
        a, b = await _gather_check_and_materialize(self, other)
        return a <= b

    # not sure what to call these
    async def __contains(self, item: Any) -> bool:
        _self, _item = await _gather_check_and_materialize(self, item)
        return _item in _self

    # conversion
    # NOTE: We aren't allowed to return ASyncFutures here :(
    def __bool__(self) -> bool:
        return bool(_materialize(self))

    def __bytes__(self) -> bytes:
        return bytes(_materialize(self))

    def __str__(self) -> str:
        return str(_materialize(self))

    def __int__(self) -> int:
        return int(_materialize(self))

    def __float__(self) -> float:
        return float(_materialize(self))

    # WIP internals

    @property
    def __dependants__(self) -> Set["ASyncFuture"]:
        """
        Returns the set of dependants for this `ASyncFuture`, including nested dependants.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=42))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=10), dependencies=[future1])
            >>> dependants = future1.__dependants__
            >>> future2 in dependants
            True
        """
        dependants = set()
        for dep in self.__dependants:
            dependants.add(dep)
            dependants.union(dep.__dependants__)
        return dependants

    @property
    def __dependencies__(self) -> Set["ASyncFuture"]:
        """
        Returns the set of dependencies for this `ASyncFuture`, including nested dependencies.

        Example:
            >>> future1 = ASyncFuture(asyncio.sleep(1, result=42))
            >>> future2 = ASyncFuture(asyncio.sleep(1, result=10), dependencies=[future1])
            >>> dependencies = future2.__dependencies__
            >>> future1 in dependencies
            True
        """
        dependencies = set()
        for dep in self.__dependencies:
            dependencies.add(dep)
            dependencies.union(dep.__dependencies__)
        return dependencies

    def __sizeof__(self) -> int:
        if isinstance(self.__awaitable__, Coroutine):
            return sum(sys.getsizeof(v) for v in self.__awaitable__.cr_frame.f_locals.values())
        elif isinstance(self.__awaitable__, Future):
            raise NotImplementedError
        raise NotImplementedError


@final
class _ASyncFutureWrappedFn(Callable[P, ASyncFuture[T]]):
    """
    A callable class to wrap functions and return `ASyncFuture` objects.

    This class is used internally by the `future` decorator to wrap a function
    and return an `ASyncFuture` when the function is called. It allows the
    function to be executed asynchronously and its result to be awaited.

    Example:
        >>> def sync_fn():
        ...     return 42
        >>> wrapped_fn = _ASyncFutureWrappedFn(sync_fn)
        >>> future = wrapped_fn()
        >>> isinstance(future, ASyncFuture)
        True

    Note:
        This is not part of the public API. Use the `future` decorator instead.
    """

    __slots__ = "callable", "wrapped", "_callable_name"

    def __init__(
        self,
        callable: AnyFn[P, T] = None,
        **kwargs: Unpack[ModifierKwargs],
    ):
        from a_sync import a_sync

        if callable:
            self.callable = callable
            """The callable function."""

            self._callable_name = callable.__name__
            """The name of the callable function."""

            a_sync_callable = a_sync(callable, default="async", **kwargs)

            @wraps(callable)
            def future_wrap(*args: P.args, **kwargs: P.kwargs) -> "ASyncFuture[T]":
                return ASyncFuture(a_sync_callable(*args, **kwargs, sync=False))

            self.wrapped = future_wrap
            """The wrapped function returning ASyncFuture."""
        else:
            self.wrapped = partial(_ASyncFutureWrappedFn, **kwargs)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> ASyncFuture[T]:
        return self.wrapped(*args, **kwargs)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.callable}>"

    def __get__(
        self, instance: I, owner: Type[I]
    ) -> Union[Self, "_ASyncFutureInstanceMethod[I, P, T]"]:
        return self if owner is None else _ASyncFutureInstanceMethod(self, instance)


@final
class _ASyncFutureInstanceMethod(Generic[I, P, T]):
    # NOTE: probably could just replace this with functools.partial
    """
    A class to handle instance methods wrapped as `ASyncFuture`.

    This class is used internally to manage instance methods that are wrapped
    by `_ASyncFutureWrappedFn`. It ensures that the method is bound to the
    instance and returns an `ASyncFuture` when called.

    Example:
        >>> class MyClass:
        ...     @_ASyncFutureWrappedFn
        ...     def method(self):
        ...         return 42
        >>> instance = MyClass()
        >>> future = instance.method()
        >>> isinstance(future, ASyncFuture)
        True

    Note:
        This is not part of the public API. Use the `future` decorator instead.
    """

    __module__: str
    """The module name of the wrapper."""

    __name__: str
    """The name of the wrapper."""

    __qualname__: str
    """The qualified name of the wrapper."""

    __doc__: Optional[str]
    """The docstring of the wrapper."""

    __annotations__: Dict[str, Any]
    """The annotations of the wrapper."""

    __instance: I
    """The instance to which the method is bound."""

    __wrapper: _ASyncFutureWrappedFn[P, T]
    """The wrapper function."""

    def __init__(
        self,
        wrapper: _ASyncFutureWrappedFn[P, T],
        instance: I,
    ) -> None:  # sourcery skip: use-contextlib-suppress
        try:
            self.__module__ = wrapper.__module__
        except AttributeError:
            pass
        try:
            self.__name__ = wrapper.__name__
        except AttributeError:
            pass
        try:
            self.__qualname__ = wrapper.__qualname__
        except AttributeError:
            pass
        try:
            self.__doc__ = wrapper.__doc__
        except AttributeError:
            pass
        try:
            self.__annotations__ = wrapper.__annotations__
        except AttributeError:
            pass
        try:
            self.__dict__.update(wrapper.__dict__)
        except AttributeError:
            pass
        self.__instance = instance
        self.__wrapper = wrapper

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} for {self.__wrapper.callable} bound to {self.__instance}>"
        )

    def __call__(self, /, *fn_args: P.args, **fn_kwargs: P.kwargs) -> T:
        return self.__wrapper(self.__instance, *fn_args, **fn_kwargs)


__all__ = ["future", "ASyncFuture"]
