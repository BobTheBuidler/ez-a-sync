from a_sync._typing import *
import functools
from _typeshed import Incomplete
from a_sync import TaskMapping as TaskMapping
from a_sync.a_sync.method import (
    ASyncBoundMethod as ASyncBoundMethod,
    ASyncBoundMethodAsyncDefault as ASyncBoundMethodAsyncDefault,
    ASyncBoundMethodSyncDefault as ASyncBoundMethodSyncDefault,
)
from a_sync.a_sync.modifiers.manager import ModifierManager as ModifierManager
from typing import Any

logger: Incomplete

class _ModifiedMixin:
    """
    A mixin class for internal use that provides functionality for applying modifiers to functions.

    This class is used as a base for :class:`~ASyncFunction` and its variants, such as
    `ASyncFunctionAsyncDefault` and `ASyncFunctionSyncDefault`, to handle the application
    of async and sync modifiers to functions. Modifiers can alter the behavior of functions,
    such as converting sync functions to async, applying caching, or rate limiting.

    See Also:
        - :class:`~ASyncFunction`
        - :class:`~ModifierManager`
    """

    modifiers: ModifierManager
    @functools.cached_property
    def default(self) -> DefaultMode:
        """
        Gets the default execution mode (sync, async, or None) for the function.

        Returns:
            The default execution mode.

        See Also:
            - :attr:`ModifierManager.default`
        """

class ASyncFunction(_ModifiedMixin, Generic[P, T]):
    """
    A callable wrapper object that can be executed both synchronously and asynchronously.

    This class wraps a function or coroutine function, allowing it to be called in both
    synchronous and asynchronous contexts. It provides a flexible interface for handling
    different execution modes and applying various modifiers to the function\'s behavior.

    The class supports various modifiers that can alter the behavior of the function,
    such as caching, rate limiting, and execution in specific contexts (e.g., thread pools).

    Note:
        The logic for determining whether to execute the function synchronously or asynchronously
        is handled by the `self.fn` property, which checks for flags in the `kwargs` and defers
        to the default execution mode if no flags are specified.

    Example:
        async def my_coroutine(x: int) -> str:
            return str(x)

        func = ASyncFunction(my_coroutine)

        # Synchronous call
        result = func(5, sync=True)  # returns "5"

        # Asynchronous call
        result = await func(5)  # returns "5"

    See Also:
        - :class:`_ModifiedMixin`
        - :class:`ModifierManager`
    """

    @overload
    def __init__(self, fn: CoroFn[P, T], **modifiers: Unpack[ModifierKwargs]) -> None:
        """
        Initializes an ASyncFunction instance for a coroutine function.

        Args:
            fn: The coroutine function to wrap.
            **modifiers: Keyword arguments for function modifiers.

        Example:
            async def my_coroutine(x: int) -> str:
                return str(x)

            func = ASyncFunction(my_coroutine, cache_type='memory')
        """

    @overload
    def __init__(self, fn: SyncFn[P, T], **modifiers: Unpack[ModifierKwargs]) -> None:
        """
        Initializes an ASyncFunction instance for a synchronous function.

        Args:
            fn: The synchronous function to wrap.
            **modifiers: Keyword arguments for function modifiers.

        Example:
            def my_function(x: int) -> str:
                return str(x)

            func = ASyncFunction(my_function, runs_per_minute=60)
        """

    @overload
    def __call__(self, *args: P.args, sync: Literal[True], **kwargs: P.kwargs) -> T:
        """
        Calls the wrapped function synchronously.

        Args:
            *args: Positional arguments to pass to the wrapped function.
            sync: Must be True to indicate synchronous execution.
            **kwargs: Keyword arguments to pass to the wrapped function.

        Example:
            result = func(5, sync=True)
        """

    @overload
    def __call__(
        self, *args: P.args, sync: Literal[False], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]:
        """
        Calls the wrapped function asynchronously.

        Args:
            *args: Positional arguments to pass to the wrapped function.
            sync: Must be False to indicate asynchronous execution.
            **kwargs: Keyword arguments to pass to the wrapped function.

        Example:
            result = await func(5, sync=False)
        """

    @overload
    def __call__(self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs) -> T:
        """
        Calls the wrapped function synchronously.

        Args:
            *args: Positional arguments to pass to the wrapped function.
            asynchronous: Must be False to indicate synchronous execution.
            **kwargs: Keyword arguments to pass to the wrapped function.

        Example:
            result = func(5, asynchronous=False)
        """

    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[True], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]:
        """
        Calls the wrapped function asynchronously.

        Args:
            *args: Positional arguments to pass to the wrapped function.
            asynchronous: Must be True to indicate asynchronous execution.
            **kwargs: Keyword arguments to pass to the wrapped function.

        Example:
            result = await func(5, asynchronous=True)
        """

    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MaybeCoro[T]:
        """
        Calls the wrapped function using the default execution mode.

        Args:
            *args: Positional arguments to pass to the wrapped function.
            **kwargs: Keyword arguments to pass to the wrapped function.

        Example:
            result = func(5)
        """

    @functools.cached_property
    def fn(self):
        """
        Returns the final wrapped version of :attr:`ASyncFunction._fn` decorated with all of the a_sync goodness.

        Returns:
            The final wrapped function.

        See Also:
            - :meth:`_async_wrap`
            - :meth:`_sync_wrap`
        """

    def map(
        self,
        *iterables: AnyIterable[P.args],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **function_kwargs: P.kwargs
    ) -> TaskMapping[P, T]:
        """
        Creates a TaskMapping for the wrapped function with the given iterables.

        Args:
            *iterables: Iterable objects to be used as arguments for the function.
            concurrency: Optional maximum number of concurrent tasks.
            task_name: Optional name for the tasks.
            **function_kwargs: Additional keyword arguments to pass to the function.

        Returns:
            A TaskMapping object for managing concurrent execution.

        See Also:
            - :class:`TaskMapping`
        """

    async def any(
        self,
        *iterables: AnyIterable[P.args],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **function_kwargs: P.kwargs
    ) -> bool:
        """
        Checks if any result of the function applied to the iterables is truthy.

        Args:
            *iterables: Iterable objects to be used as arguments for the function.
            concurrency: Optional maximum number of concurrent tasks.
            task_name: Optional name for the tasks.
            **function_kwargs: Additional keyword arguments to pass to the function.

        Returns:
            True if any result is truthy, otherwise False.

        See Also:
            - :meth:`map`
        """

    async def all(
        self,
        *iterables: AnyIterable[P.args],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **function_kwargs: P.kwargs
    ) -> bool:
        """
        Checks if all results of the function applied to the iterables are truthy.

        Args:
            *iterables: Iterable objects to be used as arguments for the function.
            concurrency: Optional maximum number of concurrent tasks.
            task_name: Optional name for the tasks.
            **function_kwargs: Additional keyword arguments to pass to the function.

        Returns:
            True if all results are truthy, otherwise False.

        See Also:
            - :meth:`map`
        """

    async def min(
        self,
        *iterables: AnyIterable[P.args],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **function_kwargs: P.kwargs
    ) -> T:
        """
        Finds the minimum result of the function applied to the iterables.

        Args:
            *iterables: Iterable objects to be used as arguments for the function.
            concurrency: Optional maximum number of concurrent tasks.
            task_name: Optional name for the tasks.
            **function_kwargs: Additional keyword arguments to pass to the function.

        Returns:
            The minimum result.

        See Also:
            - :meth:`map`
        """

    async def max(
        self,
        *iterables: AnyIterable[P.args],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **function_kwargs: P.kwargs
    ) -> T:
        """
        Finds the maximum result of the function applied to the iterables.

        Args:
            *iterables: Iterable objects to be used as arguments for the function.
            concurrency: Optional maximum number of concurrent tasks.
            task_name: Optional name for the tasks.
            **function_kwargs: Additional keyword arguments to pass to the function.

        Returns:
            The maximum result.

        See Also:
            - :meth:`map`
        """

    async def sum(
        self,
        *iterables: AnyIterable[P.args],
        concurrency: Optional[int] = None,
        task_name: str = "",
        **function_kwargs: P.kwargs
    ) -> T:
        """
        Calculates the sum of the results of the function applied to the iterables.

        Args:
            *iterables: Iterable objects to be used as arguments for the function.
            concurrency: Optional maximum number of concurrent tasks.
            task_name: Optional name for the tasks.
            **function_kwargs: Additional keyword arguments to pass to the function.

        Returns:
            The sum of the results.

        See Also:
            - :meth:`map`
        """
    __docstring_append__: str

class ASyncDecorator(_ModifiedMixin):
    modifiers: Incomplete
    def __init__(self, **modifiers: Unpack[ModifierKwargs]) -> None:
        """
        Initializes an ASyncDecorator instance.

        Args:
            **modifiers: Keyword arguments for function modifiers.

        Raises:
            ValueError: If 'default' is not 'sync', 'async', or None.

        See Also:
            - :class:`ModifierManager`
        """

    def validate_inputs(self) -> None:
        """
        Validates the input modifiers.

        Raises:
            ValueError: If 'default' is not 'sync', 'async', or None.

        See Also:
            - :attr:`ModifierManager.default`
        """

    @overload
    def __call__(self, func: AnyFn[Concatenate[B, P], T]) -> ASyncBoundMethod[B, P, T]:
        """
        Decorates a bound method with async or sync behavior based on the default modifier.

        Args:
            func: The bound method to decorate.

        Returns:
            An ASyncBoundMethod instance with the appropriate default behavior.

        See Also:
            - :class:`ASyncBoundMethod`
        """

    @overload
    def __call__(self, func: AnyFn[P, T]) -> ASyncFunction[P, T]:
        """
        Decorates a function with async or sync behavior based on the default modifier.

        Args:
            func: The function to decorate.

        Returns:
            An ASyncFunction instance with the appropriate default behavior.

        See Also:
            - :class:`ASyncFunction`
        """

class ASyncFunctionSyncDefault(ASyncFunction[P, T]):
    """A specialized :class:`~ASyncFunction` that defaults to synchronous execution.

    This class is used when the :func:`~a_sync` decorator is applied with `default=\'sync\'`.
    It provides type hints to indicate that the default call behavior is synchronous and
    supports IDE type checking for most use cases.

    The wrapped function can still be called asynchronously by passing `sync=False`
    or `asynchronous=True` as a keyword argument.

    Example:
        @a_sync(default=\'sync\')
        async def my_function(x: int) -> str:
            return str(x)

        # Synchronous call (default behavior)
        result = my_function(5)  # returns "5"

        # Asynchronous call
        result = await my_function(5, sync=False)  # returns "5"
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
    __docstring_append__: str

class ASyncFunctionAsyncDefault(ASyncFunction[P, T]):
    """
    A specialized :class:`~ASyncFunction` that defaults to asynchronous execution.

    This class is used when the :func:`~a_sync` decorator is applied with `default=\'async\'`.
    It provides type hints to indicate that the default call behavior is asynchronous
    and supports IDE type checking for most use cases.

    The wrapped function can still be called synchronously by passing `sync=True`
    or `asynchronous=False` as a keyword argument.

    Example:
        @a_sync(default=\'async\')
        async def my_function(x: int) -> str:
            return str(x)

        # Asynchronous call (default behavior)
        result = await my_function(5)  # returns "5"

        # Synchronous call
        result = my_function(5, sync=True)  # returns "5"
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
    __docstring_append__: str

class ASyncDecoratorSyncDefault(ASyncDecorator):
    @overload
    def __call__(self, func: AnyFn[Concatenate[B, P], T]) -> ASyncBoundMethodSyncDefault[P, T]:
        """
        Decorates a bound method with synchronous default behavior.

        Args:
            func: The bound method to decorate.

        Returns:
            An ASyncBoundMethodSyncDefault instance with synchronous default behavior.

        See Also:
            - :class:`ASyncBoundMethodSyncDefault`
        """

    @overload
    def __call__(self, func: AnyBoundMethod[P, T]) -> ASyncFunctionSyncDefault[P, T]:
        """
        Decorates a bound method with synchronous default behavior.

        Args:
            func: The bound method to decorate.

        Returns:
            An ASyncFunctionSyncDefault instance with synchronous default behavior.

        See Also:
            - :class:`ASyncFunctionSyncDefault`
        """

    @overload
    def __call__(self, func: AnyFn[P, T]) -> ASyncFunctionSyncDefault[P, T]:
        """
        Decorates a function with synchronous default behavior.

        Args:
            func: The function to decorate.

        Returns:
            An ASyncFunctionSyncDefault instance with synchronous default behavior.

        See Also:
            - :class:`ASyncFunctionSyncDefault`
        """

class ASyncDecoratorAsyncDefault(ASyncDecorator):
    @overload
    def __call__(self, func: AnyFn[Concatenate[B, P], T]) -> ASyncBoundMethodAsyncDefault[P, T]:
        """
        Decorates a bound method with asynchronous default behavior.

        Args:
            func: The bound method to decorate.

        Returns:
            An ASyncBoundMethodAsyncDefault instance with asynchronous default behavior.

        See Also:
            - :class:`ASyncBoundMethodAsyncDefault`
        """

    @overload
    def __call__(self, func: AnyBoundMethod[P, T]) -> ASyncFunctionAsyncDefault[P, T]:
        """
        Decorates a bound method with asynchronous default behavior.

        Args:
            func: The bound method to decorate.

        Returns:
            An ASyncFunctionAsyncDefault instance with asynchronous default behavior.

        See Also:
            - :class:`ASyncFunctionAsyncDefault`
        """

    @overload
    def __call__(self, func: AnyFn[P, T]) -> ASyncFunctionAsyncDefault[P, T]:
        """
        Decorates a function with asynchronous default behavior.

        Args:
            func: The function to decorate.

        Returns:
            An ASyncFunctionAsyncDefault instance with asynchronous default behavior.

        See Also:
            - :class:`ASyncFunctionAsyncDefault`
        """
