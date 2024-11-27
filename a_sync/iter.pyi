from a_sync._typing import *
import weakref
from _typeshed import Incomplete
from collections.abc import Generator
from typing import Any

__all__ = [
    "ASyncIterable",
    "ASyncIterator",
    "ASyncFilter",
    "ASyncSorter",
    "ASyncGeneratorFunction",
]

SortKey = SyncFn[T, bool]
ViewFn = AnyFn[T, bool]

class _AwaitableAsyncIterableMixin(AsyncIterable[T]):
    """
    A mixin class defining logic for making an AsyncIterable awaitable.

    When awaited, a list of all elements will be returned.

    Example:
        You must subclass this mixin class and define your own `__aiter__` method as shown below.

        >>> class MyAwaitableAIterable(_AwaitableAsyncIterableMixin):
        ...    async def __aiter__(self):
        ...        for i in range(4):
        ...            yield i

        >>> aiterable = MyAwaitableAIterable()
        >>> await aiterable
        [0, 1, 2, 3]
    """

    __wrapped__: AsyncIterable[T]
    def __await__(self) -> Generator[Any, Any, List[T]]:
        """
        Asynchronously iterate through the {cls} and return all {obj}.

        Returns:
            A list of the {obj} yielded by the {cls}.
        """

    @property
    def materialized(self) -> List[T]:
        """
        Synchronously iterate through the {cls} and return all {obj}.

        Returns:
            A list of the {obj} yielded by the {cls}.
        """

    def sort(self, *, key: SortKey[T] = None, reverse: bool = False) -> ASyncSorter[T]:
        """
        Sort the {obj} yielded by the {cls}.

        Args:
            key (optional): A function of one argument that is used to extract a comparison key from each list element. If None, the elements themselves will be sorted. Defaults to None.
            reverse (optional): If True, the yielded elements will be sorted in reverse order. Defaults to False.

        Returns:
            An instance of :class:`~ASyncSorter` that will yield the {obj} yielded from this {cls}, but sorted.
        """

    def filter(self, function: ViewFn[T]) -> ASyncFilter[T]:
        """
        Filters the {obj} yielded by the {cls} based on a function.

        Args:
            function: A function that returns a boolean that indicates if an item should be included in the filtered result. Can be sync or async.

        Returns:
            An instance of :class:`~ASyncFilter` that yields the filtered {obj} from the {cls}.
        """

    def __init_subclass__(cls, **kwargs) -> None: ...

class ASyncIterable(_AwaitableAsyncIterableMixin[T], Iterable[T]):
    """
    A hybrid Iterable/AsyncIterable implementation designed to offer
    dual compatibility with both synchronous and asynchronous
    iteration protocols.

    This class allows objects to be iterated over using either a
    standard `for` loop or an `async for` loop, making it versatile
    in scenarios where the mode of iteration (synchronous or asynchronous)
    needs to be flexible or is determined at runtime.

    The class achieves this by implementing both `__iter__` and `__aiter__`
    methods, enabling it to return appropriate iterator objects that can
    handle synchronous and asynchronous iteration, respectively. However,
    note that synchronous iteration relies on the :class:`ASyncIterator`
    class, which uses `asyncio.get_event_loop().run_until_complete` to
    fetch items. This can raise a `RuntimeError` if the event loop is
    already running, and in such cases, a :class:`~a_sync.exceptions.SyncModeInAsyncContextError`
    is raised from the `RuntimeError`.

    Example:
        >>> async_iterable = ASyncIterable(some_async_iterable)
        >>> async for item in async_iterable:
        ...     print(item)
        >>> for item in async_iterable:
        ...     print(item)

    See Also:
        - :class:`ASyncIterator`
        - :class:`ASyncFilter`
        - :class:`ASyncSorter`
    """

    @classmethod
    def wrap(cls, wrapped: AsyncIterable[T]) -> ASyncIterable[T]:
        """Class method to wrap an AsyncIterable for backward compatibility."""
    __wrapped__: Incomplete
    def __init__(self, async_iterable: AsyncIterable[T]) -> None:
        """
        Initializes the ASyncIterable with an async iterable.

        Args:
            async_iterable: The async iterable to wrap.
        """

    def __aiter__(self) -> AsyncIterator[T]:
        """
        Return an async iterator that yields {obj} from the {cls}.
        """

    def __iter__(self) -> Iterator[T]:
        """
        Return an iterator that yields {obj} from the {cls}.

        Note:
            Synchronous iteration leverages :class:`ASyncIterator`, which uses :meth:`asyncio.BaseEventLoop.run_until_complete` to fetch items.
            :meth:`ASyncIterator.__next__` raises a :class:`~a_sync.exceptions.SyncModeInAsyncContextError` if the event loop is already running.

            If you encounter a :class:`~a_sync.exceptions.SyncModeInAsyncContextError`, you are likely working in an async codebase
            and should consider asynchronous iteration using :meth:`__aiter__` and :meth:`__anext__` instead.
        """

class ASyncIterator(_AwaitableAsyncIterableMixin[T], Iterator[T]):
    """
    A hybrid Iterator/AsyncIterator implementation that bridges the gap between synchronous and asynchronous iteration. This class provides a unified interface for iteration that can seamlessly operate in both synchronous (`for` loop) and asynchronous (`async for` loop) contexts. It allows the wrapping of asynchronous iterable objects or async generator functions, making them usable in synchronous code without explicitly managing event loops or asynchronous context switches.

    By implementing both `__next__` and `__anext__` methods, ASyncIterator enables objects to be iterated using standard iteration protocols while internally managing the complexities of asynchronous iteration. This design simplifies the use of asynchronous iterables in environments or frameworks that are not inherently asynchronous, such as standard synchronous functions or older codebases being gradually migrated to asynchronous IO.

    Note:
        Synchronous iteration with `ASyncIterator` uses `asyncio.get_event_loop().run_until_complete`, which can raise a `RuntimeError` if the event loop is already running. In such cases, a :class:`~a_sync.exceptions.SyncModeInAsyncContextError` is raised from the `RuntimeError`, indicating that synchronous iteration is not possible in an already running event loop.

    Example:
        >>> async_iterator = ASyncIterator(some_async_iterator)
        >>> async for item in async_iterator:
        ...     print(item)
        >>> for item in async_iterator:
        ...     print(item)

    See Also:
        - :class:`ASyncIterable`
        - :class:`ASyncFilter`
        - :class:`ASyncSorter`
    """

    def __next__(self) -> T:
        """
        Synchronously fetch the next item from the {cls}.

        Note:
            This method uses :meth:`asyncio.BaseEventLoop.run_until_complete` to fetch {obj}.
            This raises a :class:`RuntimeError` if the event loop is already running.
            This RuntimeError will be caught and a more descriptive :class:`~a_sync.exceptions.SyncModeInAsyncContextError` will be raised in its place.

            If you encounter a :class:`~a_sync.exceptions.SyncModeInAsyncContextError`, you are likely working in an async codebase
            and should consider asynchronous iteration using :meth:`__aiter__` and :meth:`__anext__` instead.

        Raises:
            StopIteration: Once all {obj} have been fetched from the {cls}.
            SyncModeInAsyncContextError: If the event loop is already running.

        """
    __wrapped__: Incomplete
    def __init__(self, async_iterator: AsyncIterator[T]) -> None:
        """
        Initializes the ASyncIterator with an async iterator.

        Args:
            async_iterator: The async iterator to wrap.
        """

    def __anext__(self) -> Coroutine[Any, Any, T]:
        """
        Asynchronously fetch the next item from the {cls}.

        Raises:
            :class:`StopAsyncIteration`: Once all {obj} have been fetched from the {cls}.
        """

    def __iter__(self) -> Self:
        """
        Return the {cls} for iteration.

        Note:
            Synchronous iteration uses :meth:`asyncio.BaseEventLoop.run_until_complete` to fetch {obj}.
            This raises a :class:`RuntimeError` if the event loop is already running.
            This RuntimeError will be caught and a more descriptive :class:`~a_sync.exceptions.SyncModeInAsyncContextError` will be raised in its place.

            If you encounter a :class:`~a_sync.exceptions.SyncModeInAsyncContextError`, you are likely working in an async codebase
            and should consider asynchronous iteration using :meth:`__aiter__` and :meth:`__anext__` instead.
        """

    def __aiter__(self) -> Self:
        """Return the {cls} for aiteration."""

class ASyncGeneratorFunction(Generic[P, T]):
    """
    Encapsulates an asynchronous generator function, providing a mechanism to use it as an asynchronous iterator with enhanced capabilities. This class wraps an async generator function, allowing it to be called with parameters and return an :class:`~ASyncIterator` object. It is particularly useful for situations where an async generator function needs to be used in a manner that is consistent with both synchronous and asynchronous execution contexts.

    The ASyncGeneratorFunction class supports dynamic binding to instances, enabling it to be used as a method on class instances. When accessed as a descriptor, it automatically handles the binding to the instance, thereby allowing the wrapped async generator function to be invoked with instance context ('self') automatically provided. This feature is invaluable for designing classes that need to expose asynchronous generators as part of their interface while maintaining the ease of use and calling semantics similar to regular methods.

    By providing a unified interface to asynchronous generator functions, this class facilitates the creation of APIs that are flexible and easy to use in a wide range of asynchronous programming scenarios. It abstracts away the complexities involved in managing asynchronous generator lifecycles and invocation semantics, making it easier for developers to integrate asynchronous iteration patterns into their applications.

    Example:
        >>> async def my_async_gen():
        ...     yield 1
        ...     yield 2
        >>> async_gen_func = ASyncGeneratorFunction(my_async_gen)
        >>> for item in async_gen_func():
        ...     print(item)

    See Also:
        - :class:`ASyncIterator`
        - :class:`ASyncIterable`
    """

    __weakself__: weakref.ref[object]
    field_name: Incomplete
    __wrapped__: Incomplete
    def __init__(self, async_gen_func: AsyncGenFunc[P, T], instance: Any = None) -> None:
        """
        Initializes the ASyncGeneratorFunction with the given async generator function and optionally an instance.

        Args:
            async_gen_func: The async generator function to wrap.
            instance (optional): The object to bind to the function, if applicable.
        """

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> ASyncIterator[T]:
        """
        Calls the wrapped async generator function with the given arguments and keyword arguments, returning an :class:`ASyncIterator`.

        Args:
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
        """

    def __get__(self, instance: V, owner: Type[V]) -> ASyncGeneratorFunction[P, T]:
        """Descriptor method to make the function act like a non-data descriptor."""

    @property
    def __self__(self) -> object: ...

class _ASyncView(ASyncIterator[T]):
    """
    Internal mixin class containing logic for creating specialized views for :class:`~ASyncIterable` objects.
    """

    __aiterator__: Optional[AsyncIterator[T]]
    __iterator__: Optional[Iterator[T]]
    __wrapped__: Incomplete
    def __init__(self, function: ViewFn[T], iterable: AnyIterable[T]) -> None:
        """
        Initializes the {cls} with a function and an iterable.

        Args:
            function: A function to apply to the items in the iterable.
            iterable: An iterable or an async iterable yielding objects to which `function` will be applied.
        """

class ASyncFilter(_ASyncView[T]):
    """
    An async filter class that filters items of an async iterable based on a provided function.

    This class inherits from :class:`~_ASyncView` and provides the functionality to asynchronously
    iterate over items, applying the filter function to each item to determine if it should be
    included in the result. The filter function can be either synchronous or asynchronous.

    Example:
        >>> async def is_even(x):
        ...     return x % 2 == 0
        >>> filtered_iterable = ASyncFilter(is_even, some_async_iterable)
        >>> async for item in filtered_iterable:
        ...     print(item)

    See Also:
        - :class:`ASyncIterable`
        - :class:`ASyncIterator`
        - :class:`ASyncSorter`
    """

    async def __anext__(self) -> T: ...

class ASyncSorter(_ASyncView[T]):
    """
    An async sorter class that sorts items of an async iterable based on a provided key function.

    This class inherits from :class:`~_ASyncView` and provides the functionality to asynchronously
    iterate over items, applying the key function to each item for sorting. The key function can be
    either synchronous or asynchronous. Note that the ASyncSorter instance can only be consumed once.

    Example:
        >>> sorted_iterable = ASyncSorter(some_async_iterable, key=lambda x: x.value)
        >>> async for item in sorted_iterable:
        ...     print(item)

    See Also:
        - :class:`ASyncIterable`
        - :class:`ASyncIterator`
        - :class:`ASyncFilter`
    """

    reversed: bool
    def __init__(
        self, iterable: AsyncIterable[T], *, key: SortKey[T] = None, reverse: bool = False
    ) -> None:
        """
        Initializes the ASyncSorter with an iterable and an optional sorting configuration (key function, and reverse flag).

        Args:
            iterable: The async iterable to sort.
            key (optional): A function of one argument that is used to extract a comparison key from each list element. If none is provided, elements themselves will be sorted. Defaults to None.
            reverse (optional): If True, the list elements will be sorted in reverse order. Defaults to False.
        """

    def __aiter__(self) -> AsyncIterator[T]:
        """
        Return an async iterator for the {cls}.

        Raises:
            RuntimeError: If the ASyncSorter instance has already been consumed.

        Returns:
            An async iterator that will yield the sorted {obj}.
        """

    def __anext__(self) -> T: ...
