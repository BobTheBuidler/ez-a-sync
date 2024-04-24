
import asyncio
import functools
import inspect
import logging

from async_property import async_cached_property

from a_sync import _helpers
from a_sync._typing import *


logger = logging.getLogger(__name__)

class _AwaitableAsyncIterableMixin(AsyncIterable[T]):
    """
    A mixin class defining logic for awaiting an AsyncIterable
    """
    __wrapped__: AsyncIterable[T]
    def __aiter__(self) -> AsyncIterator[T]:
        "Returns an async iterator for the wrapped async iterable."
        return self.__wrapped__.__aiter__()
    def __await__(self) -> Generator[Any, Any, List[T]]:
        """Asynchronously iterates through all contents of ``Self`` and returns a ``list`` containing the results."""
        return self._materialized.__await__()
    @property
    def materialized(self) -> List[T]:
        """Iterates through all contents of ``Self`` and returns a ``list`` containing the results."""
        return _helpers._await(self._materialized)
    @async_cached_property
    async def _materialized(self) -> List[T]:
        """Asynchronously iterates through all contents of ``Self`` and returns a ``list`` containing the results."""
        return [obj async for obj in self]
    __slots__ = '__async_property__', 
    
class ASyncIterable(_AwaitableAsyncIterableMixin[T], Iterable[T]):
    """
    Description:
        A hybrid Iterable/AsyncIterable implementation designed to offer dual compatibility with both synchronous and asynchronous iteration protocols. This class allows objects to be iterated over using either a standard `for` loop or an `async for` loop, making it versatile in scenarios where the mode of iteration (synchronous or asynchronous) needs to be flexible or is determined at runtime.

        The class achieves this by implementing both `__iter__` and `__aiter__` methods, enabling it to return appropriate iterator objects that can handle synchronous and asynchronous iteration, respectively. This dual functionality is particularly useful in codebases that are transitioning between synchronous and asynchronous code, or in libraries that aim to support both synchronous and asynchronous usage patterns without requiring the user to manage different types of iterable objects.

    """
    @classmethod
    def wrap(cls, wrapped: AsyncIterable[T]) -> "ASyncIterable[T]":
        "Class method to wrap an AsyncIterable for backward compatibility."
        logger.warning("ASyncIterable.wrap will be removed soon. Please replace uses with simple instantiation ie `ASyncIterable(wrapped)`")
        return cls(wrapped)
    def __init__(self, async_iterable: AsyncIterable[T]):
        "Initializes the ASyncIterable with an async iterable."
        self.__wrapped__ = async_iterable
        "The wrapped async iterable object."
    def __repr__(self) -> str:
        return f"<{type(self).__name__} for {self.__wrapped__} at {hex(id(self))}>"
    def __iter__(self) -> Iterator[T]:
        "Returns an iterator for the wrapped async iterable."
        yield from ASyncIterator(self.__aiter__())
    __slots__ = "__wrapped__", 

AsyncGenFunc = Callable[P, Union[AsyncGenerator[T, None], AsyncIterator[T]]]

class ASyncIterator(_AwaitableAsyncIterableMixin[T], Iterator[T]):
    """
    Description:
        A hybrid Iterator/AsyncIterator implementation that bridges the gap between synchronous and asynchronous iteration. This class provides a unified interface for iteration that can seamlessly operate in both synchronous (`for` loop) and asynchronous (`async for` loop) contexts. It allows the wrapping of asynchronous iterable objects or async generator functions, making them usable in synchronous code without explicitly managing event loops or asynchronous context switches.

        By implementing both `__next__` and `__anext__` methods, ASyncIterator enables objects to be iterated using standard iteration protocols while internally managing the complexities of asynchronous iteration. This design simplifies the use of asynchronous iterables in environments or frameworks that are not inherently asynchronous, such as standard synchronous functions or older codebases being gradually migrated to asynchronous IO.

        This class is particularly useful for library developers seeking to provide a consistent iteration interface across synchronous and asynchronous code, reducing the cognitive load on users and promoting code reusability and simplicity.

    """
    def __next__(self) -> T:
        try:
            return asyncio.get_event_loop().run_until_complete(self.__anext__())
        except StopAsyncIteration as e:
            raise StopIteration from e
    @overload
    def wrap(cls, aiterator: AsyncIterator[T]) -> "ASyncIterator[T]":...
    @overload
    def wrap(cls, async_gen_func: AsyncGenFunc[P, T]) -> "ASyncGeneratorFunction[P, T]":...
    @classmethod
    def wrap(cls, wrapped):
        "Class method to wrap either an AsyncIterator or an async generator function."
        if isinstance(wrapped, AsyncIterator):
            logger.warning("This use case for ASyncIterator.wrap will be removed soon. Please replace uses with simple instantiation ie `ASyncIterator(wrapped)`")
            return cls(wrapped)
        elif inspect.isasyncgenfunction(wrapped):
            return ASyncGeneratorFunction(wrapped)
        raise TypeError(f"`wrapped` must be an AsyncIterator or an async generator function. You passed {wrapped}")
    def __init__(self, async_iterator: AsyncIterator[T]):
        "Initializes the ASyncIterator with an async iterator."
        self.__wrapped__ = async_iterator
        "The wrapped async iterator object."
    async def __anext__(self) -> T:
        "Asynchronously fetches the next item from the async iterator."
        return await self.__wrapped__.__anext__()

class ASyncGeneratorFunction(Generic[P, T]):
    """
    Description:
        Encapsulates an asynchronous generator function, providing a mechanism to use it as an asynchronous iterator with enhanced capabilities. This class wraps an async generator function, allowing it to be called with parameters and return an ASyncIterator object. It is particularly useful for situations where an async generator function needs to be used in a manner that is consistent with both synchronous and asynchronous execution contexts.

        The ASyncGeneratorFunction class supports dynamic binding to instances, enabling it to be used as a method on class instances. When accessed as a descriptor, it automatically handles the binding to the instance, thereby allowing the wrapped async generator function to be invoked with instance context ('self') automatically provided. This feature is invaluable for designing classes that need to expose asynchronous generators as part of their interface while maintaining the ease of use and calling semantics similar to regular methods.

        By providing a unified interface to asynchronous generator functions, this class facilitates the creation of APIs that are flexible and easy to use in a wide range of asynchronous programming scenarios. It abstracts away the complexities involved in managing asynchronous generator lifecycles and invocation semantics, making it easier for developers to integrate asynchronous iteration patterns into their applications.
    
    """
    def __init__(self, async_gen_func: AsyncGenFunc[P, T], instance: Any = None) -> None:
        "Initializes the ASyncGeneratorFunction with the given async generator function and optionally an instance."
        self.field_name = async_gen_func.__name__
        "The name of the async generator function."
        self.__wrapped__ = async_gen_func
        "The actual async generator function."
        self.__instance__ = instance
        "The instance the function is bound to, if any."
        functools.update_wrapper(self, self.__wrapped__)
    def __repr__(self) -> str:
        return f"<{type(self).__name__} for {self.__wrapped__} at {hex(id(self))}>"
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> ASyncIterator[T]:
        "Calls the wrapped async generator function with the given arguments and keyword arguments, returning an ASyncIterator."
        if self.__instance__ is None:
            return ASyncIterator(self.__wrapped__(*args, **kwargs))
        return ASyncIterator(self.__wrapped__(self.__instance__, *args, **kwargs))
    def __get__(self, instance: Any, owner: Any) -> "ASyncGeneratorFunction[P, T]":
        "Descriptor method to make the function act like a non-data descriptor."
        if instance is None:
            return self
        try:
            return instance.__dict__[self.field_name]
        except KeyError:
            gen_func = ASyncGeneratorFunction(self.__wrapped__, instance)
            instance.__dict__[self.field_name] = gen_func
            return gen_func
