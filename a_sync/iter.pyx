# cython: boundscheck=False
import asyncio
import copy
import inspect
import sys
import types
import typing
import weakref
from functools import lru_cache
from logging import getLogger

from cpython.object cimport PyObject, PyObject_GetIter
from cython cimport final
from typing_extensions import Self

from a_sync._typing import AnyFn, AnyIterable, P, T, SyncFn, V
from a_sync.a_sync._helpers cimport _await
from a_sync.async_property import async_cached_property
from a_sync.async_property.cached cimport AsyncCachedPropertyInstanceState
from a_sync.asyncio cimport cigather, ccreate_task_simple
from a_sync.exceptions import SyncModeInAsyncContextError
from a_sync.functools cimport update_wrapper

cdef extern from "pythoncapi_compat.h":
    int PyWeakref_GetRef(PyObject*, PyObject**)


# cdef asyncio
cdef object get_event_loop = asyncio.get_event_loop
cdef object iscoroutinefunction = asyncio.iscoroutinefunction
cdef object TimerHandle = asyncio.TimerHandle
cdef object cancel_handle = TimerHandle.cancel
del asyncio

# cdef copy
cdef object deepcopy = copy.deepcopy
del copy

# cdef inspect
cdef object isasyncgenfunction = inspect.isasyncgenfunction
cdef object isawaitable = inspect.isawaitable
del inspect

# cdef logging
cdef public object logger = getLogger(__name__)
del getLogger

# cdef types
cdef object FunctionType = types.FunctionType
del types

# cdef typing
cdef object get_args = typing.get_args
cdef object _GenericAlias = typing._GenericAlias
cdef object Any = typing.Any
cdef object AsyncIterable = typing.AsyncIterable
cdef object AsyncIterator = typing.AsyncIterator
cdef object AsyncGenerator = typing.AsyncGenerator
cdef object Callable = typing.Callable
cdef object Coroutine = typing.Coroutine
cdef object Generator = typing.Generator
cdef object Generic = typing.Generic
cdef object Iterable = typing.Iterable
cdef object Iterator = typing.Iterator
cdef object List = typing.List
cdef object Optional = typing.Optional
cdef object Type = typing.Type
cdef object TypeVar = typing.TypeVar
cdef object Union = typing.Union
cdef object overload = typing.overload
del typing

# cdef weakref
cdef object ref = weakref.ref
del weakref


cdef object SortKey, ViewFn
if sys.version_info < (3, 10):
    SortKey = SyncFn[T, bool]
    ViewFn = AnyFn[T, bool]
else:
    SortKey = SyncFn[[T], bool]
    ViewFn = AnyFn[[T], bool]
del sys

cdef object AsyncGenFunc = Callable[P, Union[AsyncGenerator[T, None], AsyncIterator[T]]]


cdef tuple[str, str] _FORMAT_PATTERNS = ("{cls}", "{obj}")


cdef class _AwaitableAsyncIterableMixin:
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

    cdef readonly object __wrapped__
    cdef readonly AsyncCachedPropertyInstanceState __async_property__

    def __cinit__(self) -> None:
        self.__async_property__ = AsyncCachedPropertyInstanceState()
        
    def __aiter__(self) -> AsyncIterator[T]:
        raise NotImplementedError
        
    def __await__(self) -> Generator[Any, Any, List[T]]:
        """
        Asynchronously iterate through the {cls} and return all {obj}.

        Returns:
            A list of the {obj} yielded by the {cls}.
        """
        return self._materialized.__await__()

    @property
    def materialized(self) -> List[T]:
        """
        Synchronously iterate through the {cls} and return all {obj}.

        Returns:
            A list of the {obj} yielded by the {cls}.
        """
        return _await(self._materialized)

    cpdef object sort(self, key: SortKey[T] = None, reverse: bool = False):
        """
        Sort the {obj} yielded by the {cls}.

        Args:
            key (optional): A function of one argument that is used to extract a comparison key from each list element. If None, the elements themselves will be sorted. Defaults to None.
            reverse (optional): If True, the yielded elements will be sorted in reverse order. Defaults to False.

        Returns:
            An instance of :class:`~ASyncSorter` that will yield the {obj} yielded from this {cls}, but sorted.
        """
        return ASyncSorter(self, key=key, reverse=reverse)

    cpdef object filter(self, function: ViewFn[T]):
        """
        Filters the {obj} yielded by the {cls} based on a function.

        Args:
            function: A function that returns a boolean that indicates if an item should be included in the filtered result. Can be sync or async.

        Returns:
            An instance of :class:`~ASyncFilter` that yields the filtered {obj} from the {cls}.
        """
        return ASyncFilter(function, self)

    @async_cached_property
    async def _materialized(self) -> List[T]:
        """
        Asynchronously iterate through the {cls} and return all {obj}.

        Returns:
            A list of the {obj} yielded by the {cls}.
        """
        return [obj async for obj in self]


cdef class _ASyncIterable(_AwaitableAsyncIterableMixin):
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
                "`async_iterable` must be an AsyncIterable. You passed {}".format(async_iterable)
            )
        self.__wrapped__ = async_iterable
        "The wrapped async iterable object."

    def __repr__(self) -> str:
        start = "<{}".format(type(self).__name__)
        if wrapped := getattr(self, "__wrapped__", None):
            start += " for {}".format(wrapped)
        return "{} at {}>".format(start, hex(id(self)))

    def __aiter__(self) -> AsyncIterator[T]:
        """
        Return an async iterator that yields {obj} from the {cls}.
        """
        return self.__wrapped__.__aiter__()
    
    def __iter__(self) -> ASyncIterator[T]:
        """
        Return an iterator that yields {obj} from the {cls}.

        Note:
            Synchronous iteration leverages :class:`ASyncIterator`, which uses :meth:`asyncio.BaseEventLoop.run_until_complete` to fetch items.
            :meth:`ASyncIterator.__next__` raises a :class:`~a_sync.exceptions.SyncModeInAsyncContextError` if the event loop is already running.

            If you encounter a :class:`~a_sync.exceptions.SyncModeInAsyncContextError`, you are likely working in an async codebase
            and should consider asynchronous iteration using :meth:`__aiter__` and :meth:`__anext__` instead.
        """
        return ASyncIterator(self.__wrapped__.__aiter__())


class ASyncIterable(_ASyncIterable):
    def __init_subclass__(cls, **kwargs) -> None:
        _init_subclass(cls, kwargs)
    def __class_getitem__(cls, arg_or_args, **kwargs) -> Type["ASyncIterable[T]"]:
        """
        This helper passes type information from subclasses to the subclass object.

        Args:
            arg_or_args: Either a single type argument or a tuple of the type arguments used.
        """
        if cls is ASyncIterable:
            if kwargs:
                raise RuntimeError("Cannot pass kwargs")
            if isinstance(arg_or_args, tuple):
                args = arg_or_args
            else:
                args = (arg_or_args,)
            return _class_getitem(cls, args)
        
        if hasattr(cls, "__parameters__"):
            return super().__class_getitem__(arg_or_args, **kwargs)
        else:
            return cls


cdef class _ASyncIterator(_AwaitableAsyncIterableMixin):
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
    cdef readonly object _anext
    cdef object _loop

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
        # If this is the first time this instance has been used synchronously, we
        # cache `loop.run_until_complete` to use it more quickly for subsequent nexts
        cdef object run_loop = self._run_loop
        if run_loop is None:
            run_loop = self._run_loop = get_event_loop().run_until_complete
            
        try:
            return run_loop(self._anext())
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
        """Class method to wrap either an AsyncIterator or an async generator function."""
        if isinstance(wrapped, AsyncIterator):
            logger.warning(
                "This use case for ASyncIterator.wrap will be removed soon. "
                "Please replace uses with simple instantiation ie `ASyncIterator(wrapped)`"
            )
            return cls(wrapped)
        
        # We're going to assume that a dev writing cython knows what they're doing.
        # Plus, we need it for this lib's internals to work properly.
        elif isasyncgenfunction(wrapped) or type(wrapped).__name__ == "cython_function_or_method":
            return ASyncGeneratorFunction(wrapped)
        
        raise TypeError(
            "`wrapped` must be an AsyncIterator or an async generator function. "
            "You passed {} of type {}".format(wrapped, type(wrapped))
        )
    
    def __init__(self, async_iterator: AsyncIterator[T]) -> None:
        """
        Initializes the ASyncIterator with an async iterator.

        Args:
            async_iterator: The async iterator to wrap.
        """
        if not isinstance(async_iterator, AsyncIterator):
            raise TypeError(
                "`async_iterator` must be an AsyncIterator. You passed {}".format(async_iterator)
            )
        self.__wrapped__ = async_iterator
        "The wrapped :class:`AsyncIterator`."
    
        self._anext = async_iterator.__anext__
        self._run_loop = None

    def __anext__(self) -> Coroutine[Any, Any, T]:
        """
        Asynchronously fetch the next item from the {cls}.

        Raises:
            :class:`StopAsyncIteration`: Once all {obj} have been fetched from the {cls}.
        """
        return self._anext()

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
        return self

    def __aiter__(self) -> Self:
        "Return the {cls} for aiteration."
        return self


class ASyncIterator(_ASyncIterator):
    def __init_subclass__(cls, **kwargs) -> None:
        _init_subclass(cls, kwargs)
    def __class_getitem__(cls, arg_or_args, **kwargs) -> Type["ASyncIterator[T]"]:
        """
        This helper passes type information from subclasses to the subclass object.

        Args:
            arg_or_args: Either a single type argument or a tuple of the type arguments used.
        """
        if cls is ASyncIterator:
            if kwargs:
                raise RuntimeError("Cannot pass kwargs")
            if isinstance(arg_or_args, tuple):
                args = arg_or_args
            else:
                args = (arg_or_args,)
            return _class_getitem(cls, args)
        
        if hasattr(cls, "__parameters__"):
            return super().__class_getitem__(arg_or_args, **kwargs)
        else:
            return cls



cdef class _ASyncGeneratorFunction:
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
        
        if instance is None:
            self.__weakself__ = None
            self.__weakself_ptr = NULL
            self._cache_handle = None
        else:
            weakself = ref(instance, _ASyncGeneratorFunction.__cancel_cache_handle)
            self.__weakself__ = weakself
            self.__weakself_ptr = <PyObject*>weakself
            self._cache_handle = self._get_cache_handle(instance)
    
    def __repr__(self) -> str:
        return "<{} for {} at {}>".format(
            type(self).__name__, 
            self.__wrapped__, 
            hex(id(self))
        )
     
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
        cdef _ASyncGeneratorFunction gen_func
        cdef dict instance_dict
        
        if instance is None:
            return self
        
        instance_dict = instance.__dict__
        
        try:
            gen_func = instance_dict[self.field_name]
        except KeyError:
            gen_func = ASyncGeneratorFunction(self.__wrapped__, instance)
            instance_dict[self.field_name] = gen_func
            
        gen_func._set_cache_handle(self._get_cache_handle(instance))
        return gen_func
    
    @property
    def __self__(self) -> object:
        cdef PyObject *weakself_ptr = self.__weakself_ptr
        cdef PyObject *instance_ptr

        if weakself_ptr is NULL:
            raise AttributeError("{} has no attribute '__self__'".format(self))
        elif PyWeakref_GetRef(weakself_ptr, &instance_ptr) == 1:
            # 1 is success
            return <object>instance_ptr
        raise ReferenceError(self)

    cdef inline void _set_cache_handle(self, object handle):
        self.__cancel_cache_handle()
        self._cache_handle = handle
    
    cdef inline object _get_cache_handle(self, object instance):
        # NOTE: we create a strong reference to instance here. I'm not sure if this is good or not but its necessary for now.
        return get_event_loop().call_later(
            300, delattr, instance, self.field_name
        )

    cdef void __cancel_cache_handle(self):
        cancel_handle(self._cache_handle)


class ASyncGeneratorFunction(_ASyncGeneratorFunction, Generic[P, T]):
    def __init__(
        self, async_gen_func: AsyncGenFunc[P, T], instance: Any = None
    ) -> None:
        _ASyncGeneratorFunction.__init__(self, async_gen_func, instance)
        update_wrapper(self, self.__wrapped__)
    


cdef class _ASyncView(_ASyncIterator):
    """
    Internal mixin class containing logic for creating specialized views for :class:`~ASyncIterable` objects.
    """
    cdef readonly object __aiterator__
    cdef readonly object __iterator__
    cdef readonly object _function

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
            self.__iterator__ = None
            self.__aiterator__ = iterable.__aiter__()
        elif isinstance(iterable, Iterable):
            self.__iterator__ = <object>PyObject_GetIter(iterable)
            self.__aiterator__ = None
        else:
            raise TypeError(
                "`iterable` must be AsyncIterable or Iterable, you passed {}".format(iterable)
            )


cdef class _ASyncFilter(_ASyncView):
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

    @final
    def __repr__(self) -> str:
        return "<{type(self).__name__} for iterator={} function={} at {}>".format(
            self.__wrapped__, self._function.__name__, hex(id(self))
        )

    @final
    async def __anext__(self) -> T:
        cdef object obj
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

    @final
    async def _check(self, obj: T) -> bool:
        """
        Checks if an object passes the filter function.

        Args:
            obj: The object to check.

        Returns:
            True if the object passes the filter, False otherwise.
        """
        cdef object checked = self._function(obj)
        return bool(await checked) if isawaitable(checked) else bool(checked)


class ASyncFilter(_ASyncFilter):
    def __init_subclass__(cls, **kwargs) -> None:
        _init_subclass(cls, kwargs)
    def __class_getitem__(cls, arg_or_args, **kwargs) -> Type["ASyncFilter[T]"]:
        """
        This helper passes type information from subclasses to the subclass object.

        Args:
            arg_or_args: Either a single type argument or a tuple of the type arguments used.
        """
        if cls is ASyncFilter:
            if kwargs:
                raise RuntimeError("Cannot pass kwargs")
            if isinstance(arg_or_args, tuple):
                args = arg_or_args
            else:
                args = (arg_or_args,)
            return _class_getitem(cls, args)
        return super().__class_getitem__(arg_or_args, **kwargs)


cdef object _key_if_no_key(object obj):
    """
    Default key function that returns the object itself if no key is provided.

    Args:
        obj: The object to return.
    """
    return obj


cdef class _ASyncSorter(_ASyncView):
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

    cdef readonly bint reversed
    cdef readonly bint _consumed
    cdef readonly object __internal

    def __cinit__(self):
        self.reversed = False
        self._consumed = False
        
    @final
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
        _ASyncView.__init__(self, _key_if_no_key if key is None else key, iterable)
        internal_aiterator = self.__sort(reverse=reverse).__aiter__()
        self.__internal = internal_aiterator
        self._anext = internal_aiterator.__anext__
        if reverse:
            self.reversed = True

    @final
    def __aiter__(self):
        """
        Return an async iterator for the {cls}.

        Raises:
            RuntimeError: If the ASyncSorter instance has already been consumed.

        Returns:
            An async iterator that will yield the sorted {obj}.
        """
        if self._consumed:
            raise RuntimeError("{} has already been consumed".format(self))
        return self

    @final
    def __repr__(self) -> str:
        cdef str rep = f"<{type(self).__name__}"
        if self.reversed:
            rep += " reversed"
        rep += " for iterator={}".format(self.__wrapped__)
        if self._function is not _key_if_no_key:
            rep += " key={}".format(self._function.__name__)
        rep += " at {}>".format(hex(id(self)))
        return rep

    @final
    def __anext__(self):
        return self._anext()

    @final
    async def __sort(self, bint reverse):
        """
        This method is internal so the original iterator can only ever be consumed once.

        Args:
            reverse: If True, the list elements will be sorted in reverse order.

        Returns:
            An async iterator that will yield the sorted items.
        """
        cdef list items, sort_tasks
        cdef object obj

        if iscoroutinefunction(self._function):
            items = []
            sort_tasks = []
            if self.__aiterator__:
                async for obj in self.__aiterator__:
                    items.append(obj)
                    sort_tasks.append(
                        ccreate_task_simple(self._function(obj))
                    )
            elif self.__iterator__:
                for obj in self.__iterator__:
                    items.append(obj)
                    sort_tasks.append(
                        ccreate_task_simple(self._function(obj))
                    )
                for sort_value, obj in sorted(
                    zip(await cigather(sort_tasks), items),
                    reverse=reverse,
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

     
class ASyncSorter(_ASyncSorter):
    def __init_subclass__(cls, **kwargs) -> None:
        _init_subclass(cls, kwargs)
    def __class_getitem__(cls, arg_or_args, **kwargs) -> Type["ASyncSorter[T]"]:
        """This helper passes type information from subclasses to the subclass object"""
        if cls is ASyncSorter:
            if kwargs:
                raise RuntimeError("Cannot pass kwargs")
            if isinstance(arg_or_args, tuple):
                args = arg_or_args
            else:
                args = (arg_or_args,)
            return _class_getitem(cls, args)
        
        if hasattr(cls, "__parameters__"):
            return super().__class_getitem__(arg_or_args, **kwargs)
        else:
            return cls

    
@lru_cache(maxsize=None)
def __class_getitem(untyped_cls: Type, tuple type_args):
    args_string = ", ".join(
        getattr(arg, "__name__", None) or repr(arg)
        for arg in type_args
    )
    typed_cls_name = f"{untyped_cls.__name__}[{args_string}]"
    typed_cls_dict = typed_class_dict = {
        "__args__": type_args, 
        "__module__": untyped_cls.__module__,
        "__qualname__": f"{untyped_cls.__qualname__}[{args_string}]",
        "__origin__": untyped_cls,
    }
    if untyped_cls.__doc__ is not None:
        typed_cls_dict["__doc__"] = str(untyped_cls.__doc__)
    if hasattr(untyped_cls, "__annotations__"):
        typed_cls_dict["__annotations__"] = untyped_cls.__annotations__
    typed_cls = type(typed_cls_name, (untyped_cls, ), typed_cls_dict)
    return typed_cls


cdef object _class_getitem = __class_getitem


cdef void _init_subclass(cls, dict kwargs):
    # Determine the type used for T in the subclass
    cdef object type_argument = T  # Default value
    cdef str type_string = ":obj:`T` objects"

    cdef object base
    cdef tuple args
    cdef str module, qualname, name
    for base in getattr(cls, "__orig_bases__", []):
        if not hasattr(base, "__args__"):
            continue
        
        args = get_args(base)
        if base in (ASyncIterable, ASyncIterator, ASyncFilter, ASyncSorter):
            raise Exception(base, args)
            
        if args and not isinstance(type_argument := args[0], TypeVar):
            module = getattr(type_argument, "__module__", "")
            qualname = getattr(type_argument, "__qualname__", "")
            name = getattr(type_argument, "__name__", "")
            
            if module and qualname:
                type_string = ":class:`~{}.{}`".format(module, qualname)
            elif module and name:
                type_string = (":class:`~{}.{}`".format(module, name))
            elif qualname:
                type_string = ":class:`{}`".format(qualname)
            elif name:
                type_string = ":class:`{}`".format(name)
            else:
                type_string = str(type_argument)

    # modify the class docstring
    cdef str new_chunk = (
        "When awaited, a list of all {} will be returned.\n".format(type_string) +
        "\n"
        "Example:\n"
        "    >>> my_object = {}(...)\n".format(cls.__name__) +
        "    >>> all_contents = await my_object\n"
        "    >>> isinstance(all_contents, list)\n"
        "    True\n"
    )

    cdef str example_text = (
        type_argument._name 
        if isinstance(type_argument, _GenericAlias) 
        else getattr(type_argument, "__name__", "")
    )
    
    if example_text:
        new_chunk += (
            "    >>> isinstance(all_contents[0], {})\n".format(example_text) +
            "    True\n"
        )

    if cls.__doc__ is None:
        cls.__doc__ = new_chunk
    elif not cls.__doc__ or cls.__doc__.endswith("\n\n"):
        cls.__doc__ += new_chunk
    elif cls.__doc__.endswith("\n"):
        cls.__doc__ += "\n{}".format(new_chunk)
    else:
        cls.__doc__ += "\n\n{}".format(new_chunk)

    # Update method docstrings by redefining methods
    # This is necessary because, by default, subclasses inherit methods from their bases
    # which means if we just update the docstring we might edit docs for unrelated objects
    is_function = lambda obj: isinstance(obj, (FunctionType, property)) or "cython_function_or_method" in type(obj).__name__

    cdef dict functions_to_redefine = {
        attr_name: attr_value
        for attr_name in dir(cls)
        if (attr_value := getattr(cls, attr_name, None))
        and is_function(attr_value)
        and attr_value.__doc__
        and any(pattern in attr_value.__doc__ for pattern in _FORMAT_PATTERNS)
    }

    cdef str function_name
    cdef object function_obj
    for function_name, function_obj in functions_to_redefine.items():
        # Create a new function object with the docstring formatted appropriately for this class
        #redefined_function_obj = FunctionType(
        #    function_obj.__code__,
        #    function_obj.__globals__,
        #    name=function_obj.__name__,
        #    argdefs=function_obj.__defaults__,
        #    closure=function_obj.__closure__,
        #)
        redefined_function_obj = None
        if hasattr(_AwaitableAsyncIterableMixin, function_name):
            base_definition = getattr(_AwaitableAsyncIterableMixin, function_name)
            if function_obj.__doc__ == base_definition.__doc__:
                redefined_function_obj = deepcopy(base_definition)
        elif cls.__name__ != "ASyncIterable" and hasattr(ASyncIterable, function_name):
            base_definition = getattr(ASyncIterable, function_name)
            if function_obj.__doc__ == base_definition.__doc__:
                redefined_function_obj = deepcopy(base_definition)
        elif cls.__name__ not in ("ASyncIterable", "ASyncIterator") and hasattr(ASyncIterator, function_name):
            base_definition = getattr(ASyncIterator, function_name)
            if function_obj.__doc__ == base_definition.__doc__:
                redefined_function_obj = deepcopy(base_definition)
        
        if redefined_function_obj is None:
            redefined_function_obj = deepcopy(function_obj)

        redefined_function_obj.__doc__ = function_obj.__doc__.format(
            cls=cls.__name__,
            obj=type_string,
        )

        if "{cls}" in redefined_function_obj.__doc__:
            raise ValueError(redefined_function_obj.__doc__)

        setattr(cls, function_name, redefined_function_obj)


__all__ = [
    "ASyncIterable",
    "ASyncIterator",
    "ASyncFilter",
    "ASyncSorter",
    "ASyncGeneratorFunction",
]
