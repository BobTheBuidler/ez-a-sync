"""
This module provides type definitions and type-related utilities for the a_sync library.
It includes various type aliases, protocols, and TypedDicts used throughout the library
to enhance type checking and provide better IDE support.
"""

import asyncio
from concurrent.futures._base import Executor
from decimal import Decimal
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Coroutine,
    DefaultDict,
    Deque,
    Dict,
    Generator,
    Generic,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    List,
    Literal,
    Mapping,
    NoReturn,
    Optional,
    Protocol,
    Set,
    Tuple,
    Type,
    TypedDict,
    TypeVar,
    Union,
    ValuesView,
    final,
    overload,
    runtime_checkable,
)

from typing_extensions import Concatenate, ParamSpec, Self, Unpack

if TYPE_CHECKING:
    from a_sync import ASyncGenericBase

    B = TypeVar("B", bound=ASyncGenericBase)
else:
    B = TypeVar("B")

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
I = TypeVar("I")
"""A :class:`TypeVar` that is used to represent instances of a common class."""

E = TypeVar("E", bound=Exception)
TYPE = TypeVar("TYPE", bound=Type)

P = ParamSpec("P")
"""A :class:`ParamSpec` used everywhere in the lib."""

Numeric = Union[int, float, Decimal]
"""Type alias for numeric values of types int, float, or Decimal."""

MaybeAwaitable = Union[Awaitable[T], T]
"""Type alias for values that may or may not be awaitable. Useful for functions that can return either an awaitable or a direct value."""

MaybeCoro = Union[Coroutine[Any, Any, T], T]
"Type alias for values that may or may not be coroutine."

CoroFn = Callable[P, Awaitable[T]]
"Type alias for any function that returns an awaitable."

SyncFn = Callable[P, T]
"""Type alias for synchronous functions."""

AnyFn = Union[CoroFn[P, T], SyncFn[P, T]]
"Type alias for any function, whether synchronous or asynchronous."


class CoroBoundMethod(Protocol[I, P, T]):
    """
    Protocol for coroutine bound methods.

    Example:
        class MyClass:
            async def my_method(self, x: int) -> str:
                return str(x)

        instance = MyClass()
        bound_method: CoroBoundMethod[MyClass, [int], str] = instance.my_method
    """

    __self__: I
    __call__: Callable[P, Awaitable[T]]


class SyncBoundMethod(Protocol[I, P, T]):
    """
    Protocol for synchronous bound methods.

    Example:
        class MyClass:
            def my_method(self, x: int) -> str:
                return str(x)

        instance = MyClass()
        bound_method: SyncBoundMethod[MyClass, [int], str] = instance.my_method
    """

    __self__: I
    __call__: Callable[P, T]


AnyBoundMethod = Union[CoroBoundMethod[Any, P, T], SyncBoundMethod[Any, P, T]]
"Type alias for any bound method, whether synchronous or asynchronous."


@runtime_checkable
class AsyncUnboundMethod(Protocol[I, P, T]):
    """
    Protocol for unbound asynchronous methods.

    An unbound method is a method that hasn't been bound to an instance of a class yet.
    It's essentially the function object itself, before it's accessed through an instance.
    """

    __get__: Callable[[I, Type], CoroBoundMethod[I, P, T]]


@runtime_checkable
class SyncUnboundMethod(Protocol[I, P, T]):
    """
    Protocol for unbound synchronous methods.

    An unbound method is a method that hasn't been bound to an instance of a class yet.
    It's essentially the function object itself, before it's accessed through an instance.
    """

    __get__: Callable[[I, Type], SyncBoundMethod[I, P, T]]


AnyUnboundMethod = Union[AsyncUnboundMethod[I, P, T], SyncUnboundMethod[I, P, T]]
"Type alias for any unbound method, whether synchronous or asynchronous."

AsyncGetterFunction = Callable[[I], Awaitable[T]]
"Type alias for asynchronous getter functions."

SyncGetterFunction = Callable[[I], T]
"Type alias for synchronous getter functions."

AnyGetterFunction = Union[AsyncGetterFunction[I, T], SyncGetterFunction[I, T]]
"Type alias for any getter function, whether synchronous or asynchronous."

AsyncDecorator = Callable[[CoroFn[P, T]], CoroFn[P, T]]
"Type alias for decorators for coroutine functions."

AsyncDecoratorOrCoroFn = Union[AsyncDecorator[P, T], CoroFn[P, T]]
"Type alias for either an asynchronous decorator or a coroutine function."

DefaultMode = Literal["sync", "async", None]
"Type alias for default modes of operation."

CacheType = Literal["memory", None]
"Type alias for cache types."

SemaphoreSpec = Optional[Union[asyncio.Semaphore, int]]
"Type alias for semaphore specifications."


class ModifierKwargs(TypedDict, total=False):
    """
    TypedDict for keyword arguments that modify the behavior of asynchronous operations.
    """

    default: DefaultMode
    cache_type: CacheType
    cache_typed: bool
    ram_cache_maxsize: Optional[int]
    ram_cache_ttl: Optional[Numeric]
    runs_per_minute: Optional[int]
    semaphore: SemaphoreSpec
    # sync modifiers
    executor: Executor


AnyIterable = Union[AsyncIterable[K], Iterable[K]]
"Type alias for any iterable, whether synchronous or asynchronous."

AnyIterableOrAwaitableIterable = Union[AnyIterable[K], Awaitable[AnyIterable[K]]]
"""
Type alias for any iterable, whether synchronous or asynchronous, 
or an awaitable that resolves to any iterable, whether synchronous or asynchronous.
"""
