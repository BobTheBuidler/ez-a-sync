import asyncio
import functools
import inspect
import logging
import sys
import weakref

from async_property import async_cached_property

from a_sync._typing import *
from a_sync.a_sync import _helpers
from a_sync.exceptions import SyncModeInAsyncContextError


logger = logging.getLogger(__name__)

if sys.version_info < (3, 10):
    SortKey = SyncFn[T, bool]
    ViewFn = AnyFn[T, bool]
else:
    SortKey = SyncFn[[T], bool]
    ViewFn = AnyFn[[T], bool]


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
        Asynchronously iterate through the {cls} and return all objects.

        Returns:
            A list of the objects yielded by the {cls}.
        """
        return self._materialized.__await__()

    @property
    def materialized(self) -> List[T]:
        """
        Synchronously iterate through the {cls} and return all objects.

        Returns:
            A list of the objects yielded by the {cls}.
        """
        return _helpers._await(self._materialized)

    def sort(
        self, *, key: SortKey[T] = None, reverse: bool = False
    ) -> "ASyncSorter[T]":
        """
        Sort the contents of the {cls}.

        Args:
            key (optional): A function of one argument that is used to extract a comparison key from each list element. If None, the elements themselves will be sorted. Defaults to None.
            reverse (optional): If True, the yielded elements will be sorted in reverse order. Defaults to False.

        Returns:
            An instance of :class:`~ASyncSorter` that will yield the objects yielded from this {cls}, but sorted.
        """
        return ASyncSorter(self, key=key, reverse=reverse)

    def filter(self, function: ViewFn[T]) -> "ASyncFilter[T]":
        """
        Filters the contents of the {cls} based on a function.

        Args:
            function: A function that returns a boolean that indicates if an item should be included in the filtered result. Can be sync or async.

        Returns:
            An instance of :class:`~ASyncFilter` that yields the filtered objects from the {cls}.
        """
        return ASyncFilter(function, self)

    @async_cached_property
    async def _materialized(self) -> List[T]:
        """
        Asynchronously iterate through the {cls} and return all objects.

        Returns:
            A list of the objects yielded by the {cls}.
        """
        return [obj async for obj in self]

    def __init_subclass__(cls, **kwargs) -> None:
        new = "When awaited, a list of all elements will be returned."

        # modify the class docstring
        if cls.__doc__ is None:
            cls.__doc__ = new
        else:
            cls.__doc__ += f"\n\n{new}"

        # format the member docstrings
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name, None)
            if attr is not None and attr.__doc__ and "{cls}" in attr.__doc__:
                attr.__doc__ = attr.__doc__.replace("{cls}", f":class:`{cls.__name__}`")

        return super().__init_subclass__(**kwargs)

    __slots__ = ("__async_property__",)


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
    def wrap(cls, wrapped: AsyncIterable[T]) -> "ASyncIterable[T]":
        "Class method to wrap an AsyncIterable for backward compatibility."
        logger.warning(
            "ASyncIterable.wrap will be removed soon. Please replace uses with simple instantiation ie `ASyncIterable(wrapped)`"
        )
        return cls(wrapped)

    def __init__(self, async_iterable: AsyncIterable[T]):
        """
        Initializes the ASyncIterable with an async iterable.

        Args:
            async_iterable: The async iterable to wrap.
        """
        if not isinstance(async_iterable, AsyncIterable):
            raise TypeError(
                f"`async_iterable` must be an AsyncIterable. You passed {async_iterable}"
            )
        self.__wrapped__ = async_iterable
        "The wrapped async iterable object."

    def __repr__(self) -> str:
        start = f"<{type(self).__name__}"
        if wrapped := getattr(self, "__wrapped__", None):
            start += f" for {self.__wrapped__}"
        return f"{start} at {hex(id(self))}>"

    def __aiter__(self) -> AsyncIterator[T]:
        """
        Return an async iterator that yields :obj:`T` objects from the {cls}.
        """
        return self.__wrapped__.__aiter__()

    def __iter__(self) -> Iterator[T]:
        """
        Return an iterator that yields :obj:`T` objects from the {cls}.

        Note:
            Synchronous iteration leverages :class:`ASyncIterator`, which uses :meth:`asyncio.BaseEventLoop.run_until_complete` to fetch items.
            :meth:`ASyncIterator.__next__` raises a :class:`~a_sync.exceptions.SyncModeInAsyncContextError` if the event loop is already running.

            If you encounter a :class:`~a_sync.exceptions.SyncModeInAsyncContextError`, you are likely working in an async codebase
            and should consider asynchronous iteration using :meth:`__aiter__` and :meth:`__anext__` instead.
        """
        yield from ASyncIterator(self.__aiter__())

    __slots__ = ("__wrapped__",)


AsyncGenFunc = Callable[P, Union[AsyncGenerator[T, None], AsyncIterator[T]]]


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
            This method uses :meth:`asyncio.BaseEventLoop.run_until_complete` to fetch items.
            This raises a :class:`RuntimeError` if the event loop is already running.
            This RuntimeError will be caught and a more descriptive :class:`~a_sync.exceptions.SyncModeInAsyncContextError` will be raised in its place.

            If you encounter a :class:`~a_sync.exceptions.SyncModeInAsyncContextError`, you are likely working in an async codebase
            and should consider asynchronous iteration using :meth:`__aiter__` and :meth:`__anext__` instead.

        Raises:
            StopIteration: Once all items have been fetched from the {cls}.
            SyncModeInAsyncContextError: If the event loop is already running.

        """
        try:
            return asyncio.get_event_loop().run_until_complete(self.__anext__())
        except StopAsyncIteration as e:
            raise StopIteration from e
        except RuntimeError as e:
            if str(e) == "This event loop is already running":
                raise SyncModeInAsyncContextError(
                    "The event loop is already running. Try iterating using `async for` instead of `for`."
                ) from e
            raise

    @overload
    def wrap(cls, aiterator: AsyncIterator[T]) -> "ASyncIterator[T]":
        """
        Wraps an AsyncIterator in an ASyncIterator.

        Args:
            aiterator: The AsyncIterator to wrap.
        """

    @overload
    def wrap(cls, async_gen_func: AsyncGenFunc[P, T]) -> "ASyncGeneratorFunction[P, T]":
        """
        Wraps an async generator function in an ASyncGeneratorFunction.

        Args:
            async_gen_func: The async generator function to wrap.
        """

    @classmethod
    def wrap(cls, wrapped):
        "Class method to wrap either an AsyncIterator or an async generator function."
        if isinstance(wrapped, AsyncIterator):
            logger.warning(
                "This use case for ASyncIterator.wrap will be removed soon. Please replace uses with simple instantiation ie `ASyncIterator(wrapped)`"
            )
            return cls(wrapped)
        elif inspect.isasyncgenfunction(wrapped):
            return ASyncGeneratorFunction(wrapped)
        raise TypeError(
            f"`wrapped` must be an AsyncIterator or an async generator function. You passed {wrapped}"
        )

    def __init__(self, async_iterator: AsyncIterator[T]):
        """
        Initializes the ASyncIterator with an async iterator.

        Args:
            async_iterator: The async iterator to wrap.
        """
        if not isinstance(async_iterator, AsyncIterator):
            raise TypeError(
                f"`async_iterator` must be an AsyncIterator. You passed {async_iterator}"
            )
        self.__wrapped__ = async_iterator
        "The wrapped :class:`AsyncIterator`."

    async def __anext__(self) -> T:
        """
        Asynchronously fetch the next item from the {cls}.

        Raises:
            :class:`StopAsyncIteration`: Once all items have been fetched from the {cls}.
        """
        return await self.__wrapped__.__anext__()

    def __iter__(self) -> Self:
        """
        Return the {cls} for iteration.

        Note:
            Synchronous iteration uses :meth:`asyncio.BaseEventLoop.run_until_complete` to fetch items.
            This raises a :class:`RuntimeError` if the event loop is already running.
            This RuntimeError will be caught and a more descriptive :class:`~a_sync.exceptions.SyncModeInAsyncContextError` will be raised in its place.

            If you encounter a :class:`~a_sync.exceptions.SyncModeInAsyncContextError`, you are likely working in an async codebase
            and should consider asynchronous iteration using :meth:`__aiter__` and :meth:`__anext__` instead.
        """
        return self

    def __aiter__(self) -> Self:
        "Return the {cls} for aiteration."
        return self


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

    _cache_handle: asyncio.TimerHandle
    "An asyncio handle used to pop the bound method from `instance.__dict__` 5 minutes after its last use."

    __weakself__: "weakref.ref[object]" = None
    "A weak reference to the instance the function is bound to, if any."

    def __init__(
        self, async_gen_func: AsyncGenFunc[P, T], instance: Any = None
    ) -> None:
        """
        Initializes the ASyncGeneratorFunction with the given async generator function and optionally an instance.

        Args:
            async_gen_func: The async generator function to wrap.
            instance (optional): The object to bind to the function, if applicable.
        """

        self.field_name = async_gen_func.__name__
        "The name of the async generator function."

        self.__wrapped__ = async_gen_func
        "The actual async generator function."

        if instance is not None:
            self._cache_handle = self.__get_cache_handle(instance)
            self.__weakself__ = weakref.ref(instance, self.__cancel_cache_handle)
        functools.update_wrapper(self, self.__wrapped__)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} for {self.__wrapped__} at {hex(id(self))}>"

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> ASyncIterator[T]:
        """
        Calls the wrapped async generator function with the given arguments and keyword arguments, returning an :class:`ASyncIterator`.

        Args:
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
        """
        if self.__weakself__ is None:
            return ASyncIterator(self.__wrapped__(*args, **kwargs))
        return ASyncIterator(self.__wrapped__(self.__self__, *args, **kwargs))

    def __get__(self, instance: V, owner: Type[V]) -> "ASyncGeneratorFunction[P, T]":
        "Descriptor method to make the function act like a non-data descriptor."
        if instance is None:
            return self
        try:
            gen_func = instance.__dict__[self.field_name]
        except KeyError:
            gen_func = ASyncGeneratorFunction(self.__wrapped__, instance)
            instance.__dict__[self.field_name] = gen_func
        gen_func._cache_handle.cancel()
        gen_func._cache_handle = self.__get_cache_handle(instance)
        return gen_func

    @property
    def __self__(self) -> object:
        try:
            instance = self.__weakself__()
        except TypeError:
            raise AttributeError(f"{self} has no attribute '__self__'") from None
        if instance is None:
            raise ReferenceError(self)
        return instance

    def __get_cache_handle(self, instance: object) -> asyncio.TimerHandle:
        # NOTE: we create a strong reference to instance here. I'm not sure if this is good or not but its necessary for now.
        return asyncio.get_event_loop().call_later(
            300, delattr, instance, self.field_name
        )

    def __cancel_cache_handle(self, instance: object) -> None:
        self._cache_handle.cancel()


class _ASyncView(ASyncIterator[T]):
    """
    Internal mixin class containing logic for creating specialized views for :class:`~ASyncIterable` objects.
    """

    __aiterator__: Optional[AsyncIterator[T]] = None
    """An optional async iterator. If None, :attr:`~_ASyncView.__iterator__` will have a value."""

    __iterator__: Optional[Iterator[T]] = None
    """An optional iterator. If None, :attr:`~_ASyncView.__aiterator__` will have a value."""

    def __init__(
        self,
        function: ViewFn[T],
        iterable: AnyIterable[T],
    ) -> None:
        """
        Initializes the {cls} with a function and an iterable.

        Args:
            function: A function to apply to the items in the iterable.
            iterable: An iterable or an async iterable yielding objects to which `function` will be applied.
        """
        self._function = function
        self.__wrapped__ = iterable
        if isinstance(iterable, AsyncIterable):
            self.__aiterator__ = iterable.__aiter__()
        elif isinstance(iterable, Iterable):
            self.__iterator__ = iterable.__iter__()
        else:
            raise TypeError(
                f"`iterable` must be AsyncIterable or Iterable, you passed {iterable}"
            )


@final
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

    def __repr__(self) -> str:
        return f"<ASyncFilter for iterator={self.__wrapped__} function={self._function.__name__} at {hex(id(self))}>"

    async def __anext__(self) -> T:
        if self.__aiterator__:
            async for obj in self.__aiterator__:
                if await self._check(obj):
                    return obj
        elif self.__iterator__:
            try:
                for obj in self.__iterator__:
                    if await self._check(obj):
                        return obj
            except StopIteration:
                pass
        else:
            raise TypeError(self.__wrapped__)
        raise StopAsyncIteration from None

    async def _check(self, obj: T) -> bool:
        """
        Checks if an object passes the filter function.

        Args:
            obj: The object to check.

        Returns:
            True if the object passes the filter, False otherwise.
        """
        checked = self._function(obj)
        return bool(await checked) if inspect.isawaitable(checked) else bool(checked)


def _key_if_no_key(obj: T) -> T:
    """
    Default key function that returns the object itself if no key is provided.

    Args:
        obj: The object to return.
    """
    return obj


@final
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

    reversed: bool = False
    _consumed: bool = False

    def __init__(
        self,
        iterable: AsyncIterable[T],
        *,
        key: SortKey[T] = None,
        reverse: bool = False,
    ) -> None:
        """
        Initializes the ASyncSorter with an iterable and an optional sorting configuration (key function, and reverse flag).

        Args:
            iterable: The async iterable to sort.
            key (optional): A function of one argument that is used to extract a comparison key from each list element. If none is provided, elements themselves will be sorted. Defaults to None.
            reverse (optional): If True, the list elements will be sorted in reverse order. Defaults to False.
        """
        super().__init__(key or _key_if_no_key, iterable)
        self.__internal = self.__sort(reverse=reverse).__aiter__()
        if reverse:
            self.reversed = True

    def __aiter__(self) -> AsyncIterator[T]:
        """
        Return an async iterator for the {cls}.

        Raises:
            RuntimeError: If the ASyncSorter instance has already been consumed.

        Returns:
            An async iterator that will yield the sorting results.
        """
        if self._consumed:
            raise RuntimeError(f"{self} has already been consumed")
        return self

    def __repr__(self) -> str:
        rep = "<ASyncSorter"
        if self.reversed:
            rep += " reversed"
        rep += f" for iterator={self.__wrapped__}"
        if self._function is not _key_if_no_key:
            rep += f" key={self._function.__name__}"
        rep += f" at {hex(id(self))}>"
        return rep

    def __anext__(self) -> T:
        return self.__internal.__anext__()

    async def __sort(self, reverse: bool) -> AsyncIterator[T]:
        """
        This method is internal so the original iterator can only ever be consumed once.

        Args:
            reverse: If True, the list elements will be sorted in reverse order.

        Returns:
            An async iterator that will yield the sorted items.
        """
        if asyncio.iscoroutinefunction(self._function):
            items = []
            sort_tasks = []
            if self.__aiterator__:
                async for obj in self.__aiterator__:
                    items.append(obj)
                    sort_tasks.append(asyncio.create_task(self._function(obj)))
            elif self.__iterator__:
                for obj in self.__iterator__:
                    items.append(obj)
                    sort_tasks.append(asyncio.create_task(self._function(obj)))
                for sort_value, obj in sorted(
                    zip(await asyncio.gather(*sort_tasks), items), reverse=reverse
                ):
                    yield obj
        else:
            if self.__aiterator__:
                items = [obj async for obj in self.__aiterator__]
            else:
                items = list(self.__iterator__)
            items.sort(key=self._function, reverse=reverse)
            for obj in items:
                yield obj
        self._consumed = True


__all__ = [
    "ASyncIterable",
    "ASyncIterator",
    "ASyncFilter",
    "ASyncSorter",
    "ASyncGeneratorFunction",
]
