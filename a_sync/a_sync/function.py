import functools
import inspect
import logging
import sys

from async_lru import _LRUCacheWrapper
from async_property.base import AsyncPropertyDescriptor  # type: ignore [import]
from async_property.cached import AsyncCachedPropertyDescriptor  # type: ignore [import]

from a_sync._typing import *
from a_sync.a_sync import _flags, _helpers, _kwargs
from a_sync.a_sync.modifiers.manager import ModifierManager

if TYPE_CHECKING:
    from a_sync import TaskMapping
    from a_sync.a_sync.method import (
        ASyncBoundMethod,
        ASyncBoundMethodAsyncDefault,
        ASyncBoundMethodSyncDefault,
    )

logger = logging.getLogger(__name__)


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

    # TODO: give me a docstring
    modifiers: ModifierManager

    __slots__ = "modifiers", "wrapped"

    def _asyncify(self, func: SyncFn[P, T]) -> CoroFn[P, T]:
        """
        Converts a synchronous function to an asynchronous one and applies async modifiers.

        Args:
            func: The synchronous function to be converted.

        Returns:
            The asynchronous version of the function with applied modifiers.

        See Also:
            - :func:`_helpers._asyncify`
            - :meth:`ModifierManager.apply_async_modifiers`
        """
        coro_fn = _helpers._asyncify(func, self.modifiers.executor)
        return self.modifiers.apply_async_modifiers(coro_fn)

    @functools.cached_property
    def _await(self) -> Callable[[Awaitable[T]], T]:
        """
        Applies sync modifiers to the _helpers._await function and caches it.

        Returns:
            The modified _await function.

        See Also:
            - :func:`_helpers._await`
            - :meth:`ModifierManager.apply_sync_modifiers`
        """
        return self.modifiers.apply_sync_modifiers(_helpers._await)

    @functools.cached_property
    def default(self) -> DefaultMode:
        """
        Gets the default execution mode (sync, async, or None) for the function.

        Returns:
            The default execution mode.

        See Also:
            - :attr:`ModifierManager.default`
        """
        return self.modifiers.default


def _validate_wrapped_fn(fn: Callable) -> None:
    """Ensures 'fn' is an appropriate function for wrapping with a_sync.

    Args:
        fn: The function to validate.

    Raises:
        TypeError: If the input is not callable.
        RuntimeError: If the function has arguments with names that conflict with viable flags.

    See Also:
        - :func:`_check_not_genfunc`
    """
    if isinstance(fn, (AsyncPropertyDescriptor, AsyncCachedPropertyDescriptor)):
        return  # These are always valid
    if not callable(fn):
        raise TypeError(f"Input is not callable. Unable to decorate {fn}")
    if isinstance(fn, _LRUCacheWrapper):
        fn = fn.__wrapped__
    _check_not_genfunc(fn)
    fn_args = inspect.getfullargspec(fn)[0]
    for flag in _flags.VIABLE_FLAGS:
        if flag in fn_args:
            raise RuntimeError(
                f"{fn} must not have any arguments with the following names: {_flags.VIABLE_FLAGS}"
            )


class ASyncFunction(_ModifiedMixin, Generic[P, T]):
    """
    A callable wrapper object that can be executed both synchronously and asynchronously.

    This class wraps a function or coroutine function, allowing it to be called in both
    synchronous and asynchronous contexts. It provides a flexible interface for handling
    different execution modes and applying various modifiers to the function's behavior.

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

    # NOTE: We can't use __slots__ here because it breaks functools.update_wrapper

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

    def __init__(
        self,
        fn: AnyFn[P, T],
        _skip_validate: bool = False,
        **modifiers: Unpack[ModifierKwargs],
    ) -> None:
        """
        Initializes an ASyncFunction instance.

        Args:
            fn: The function to wrap.
            _skip_validate: For internal use only. Skips validation of the wrapped function when its already been validated once before.
            **modifiers: Keyword arguments for function modifiers.

        See Also:
            - :func:`_validate_wrapped_fn`
            - :class:`ModifierManager`
        """
        if not _skip_validate:
            _validate_wrapped_fn(fn)

        self.modifiers = ModifierManager(modifiers)
        """A :class:`~ModifierManager` instance managing function modifiers."""

        self.__wrapped__ = fn
        """The original function that was wrapped."""

        functools.update_wrapper(self, self.__wrapped__)
        if self.__doc__ is None:
            self.__doc__ = f"Since `{self.__name__}` is an {self.__docstring_append__}"
        else:
            self.__doc__ += (
                f"\n\nSince `{self.__name__}` is an {self.__docstring_append__}"
            )

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
    def __call__(
        self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs
    ) -> T:
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

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MaybeCoro[T]:
        """
        Calls the wrapped function either synchronously or asynchronously.

        This method determines whether to execute the wrapped function synchronously
        or asynchronously based on the default mode and any provided flags. The
        decision logic is encapsulated within the `self.fn` property, which uses
        the `_run_sync` method to decide the execution mode.

        Note:
            The `self.fn` property is responsible for selecting the appropriate
            execution path (sync or async) by leveraging the `_run_sync` method.

        Args:
            *args: Positional arguments to pass to the wrapped function.
            **kwargs: Keyword arguments to pass to the wrapped function.

        Raises:
            Exception: Any exception that may be raised by the wrapped function.

        See Also:
            - :attr:`default`
            - :meth:`_run_sync`
        """
        logger.debug(
            "calling %s fn: %s with args: %s kwargs: %s", self, self.fn, args, kwargs
        )
        return self.fn(*args, **kwargs)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.__module__}.{self.__name__} at {hex(id(self))}>"

    @functools.cached_property
    def fn(self):
        # NOTE type hint doesnt work in py3.8 or py3.9, debug later
        #  -> Union[SyncFn[[CoroFn[P, T]], MaybeAwaitable[T]], SyncFn[[SyncFn[P, T]], MaybeAwaitable[T]]]:
        """
        Returns the final wrapped version of :attr:`ASyncFunction._fn` decorated with all of the a_sync goodness.

        Returns:
            The final wrapped function.

        See Also:
            - :meth:`_async_wrap`
            - :meth:`_sync_wrap`
        """
        return self._async_wrap if self._async_def else self._sync_wrap

    if sys.version_info >= (3, 11) or TYPE_CHECKING:
        # we can specify P.args in python>=3.11 but in lower versions it causes a crash. Everything should still type check correctly on all versions.
        def map(
            self,
            *iterables: AnyIterable[P.args],
            concurrency: Optional[int] = None,
            task_name: str = "",
            **function_kwargs: P.kwargs,
        ) -> "TaskMapping[P, T]":
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
            from a_sync import TaskMapping

            return TaskMapping(
                self,
                *iterables,
                concurrency=concurrency,
                name=task_name,
                **function_kwargs,
            )

        async def any(
            self,
            *iterables: AnyIterable[P.args],
            concurrency: Optional[int] = None,
            task_name: str = "",
            **function_kwargs: P.kwargs,
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
            return await self.map(
                *iterables,
                concurrency=concurrency,
                task_name=task_name,
                **function_kwargs,
            ).any(pop=True, sync=False)

        async def all(
            self,
            *iterables: AnyIterable[P.args],
            concurrency: Optional[int] = None,
            task_name: str = "",
            **function_kwargs: P.kwargs,
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
            return await self.map(
                *iterables,
                concurrency=concurrency,
                task_name=task_name,
                **function_kwargs,
            ).all(pop=True, sync=False)

        async def min(
            self,
            *iterables: AnyIterable[P.args],
            concurrency: Optional[int] = None,
            task_name: str = "",
            **function_kwargs: P.kwargs,
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
            return await self.map(
                *iterables,
                concurrency=concurrency,
                task_name=task_name,
                **function_kwargs,
            ).min(pop=True, sync=False)

        async def max(
            self,
            *iterables: AnyIterable[P.args],
            concurrency: Optional[int] = None,
            task_name: str = "",
            **function_kwargs: P.kwargs,
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
            return await self.map(
                *iterables,
                concurrency=concurrency,
                task_name=task_name,
                **function_kwargs,
            ).max(pop=True, sync=False)

        async def sum(
            self,
            *iterables: AnyIterable[P.args],
            concurrency: Optional[int] = None,
            task_name: str = "",
            **function_kwargs: P.kwargs,
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
            return await self.map(
                *iterables,
                concurrency=concurrency,
                task_name=task_name,
                **function_kwargs,
            ).sum(pop=True, sync=False)

    else:

        def map(
            self,
            *iterables: AnyIterable[Any],
            concurrency: Optional[int] = None,
            task_name: str = "",
            **function_kwargs: P.kwargs,
        ) -> "TaskMapping[P, T]":
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
            from a_sync import TaskMapping

            return TaskMapping(
                self,
                *iterables,
                concurrency=concurrency,
                name=task_name,
                **function_kwargs,
            )

        async def any(
            self,
            *iterables: AnyIterable[Any],
            concurrency: Optional[int] = None,
            task_name: str = "",
            **function_kwargs: P.kwargs,
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
            return await self.map(
                *iterables,
                concurrency=concurrency,
                task_name=task_name,
                **function_kwargs,
            ).any(pop=True, sync=False)

        async def all(
            self,
            *iterables: AnyIterable[Any],
            concurrency: Optional[int] = None,
            task_name: str = "",
            **function_kwargs: P.kwargs,
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
            return await self.map(
                *iterables,
                concurrency=concurrency,
                task_name=task_name,
                **function_kwargs,
            ).all(pop=True, sync=False)

        async def min(
            self,
            *iterables: AnyIterable[Any],
            concurrency: Optional[int] = None,
            task_name: str = "",
            **function_kwargs: P.kwargs,
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
            return await self.map(
                *iterables,
                concurrency=concurrency,
                task_name=task_name,
                **function_kwargs,
            ).min(pop=True, sync=False)

        async def max(
            self,
            *iterables: AnyIterable[Any],
            concurrency: Optional[int] = None,
            task_name: str = "",
            **function_kwargs: P.kwargs,
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
            return await self.map(
                *iterables,
                concurrency=concurrency,
                task_name=task_name,
                **function_kwargs,
            ).max(pop=True, sync=False)

        async def sum(
            self,
            *iterables: AnyIterable[Any],
            concurrency: Optional[int] = None,
            task_name: str = "",
            **function_kwargs: P.kwargs,
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
            return await self.map(
                *iterables,
                concurrency=concurrency,
                task_name=task_name,
                **function_kwargs,
            ).sum(pop=True, sync=False)

    @functools.cached_property
    def _sync_default(self) -> bool:
        """
        Determines the default execution mode (sync or async) for the function.

        If the user did not specify a default, this method defers to the function's
        definition (sync vs async def).

        Returns:
            True if the default is sync, False if async.

        See Also:
            - :attr:`default`
        """
        return (
            True
            if self.default == "sync"
            else False if self.default == "async" else not self._async_def
        )

    @functools.cached_property
    def _async_def(self) -> bool:
        """
        Checks if the wrapped function is an asynchronous function.

        Returns:
            True if the function is asynchronous, otherwise False.

        See Also:
            - :func:`asyncio.iscoroutinefunction`
        """
        return asyncio.iscoroutinefunction(self.__wrapped__)

    def _run_sync(self, kwargs: dict) -> bool:
        """
        Determines whether to run the function synchronously or asynchronously.

        This method checks for a flag in the kwargs and defers to it if present.
        If no flag is specified, it defers to the default execution mode.

        Args:
            kwargs: The keyword arguments passed to the function.

        Returns:
            True if the function should run synchronously, otherwise False.

        See Also:
            - :func:`_kwargs.get_flag_name`
            - :func:`_kwargs.is_sync`
        """
        if flag := _kwargs.get_flag_name(kwargs):
            # If a flag was specified in the kwargs, we will defer to it.
            return _kwargs.is_sync(flag, kwargs, pop_flag=True)
        else:
            # No flag specified in the kwargs, we will defer to 'default'.
            return self._sync_default

    @functools.cached_property
    def _asyncified(self) -> CoroFn[P, T]:
        """
        Converts the wrapped function to an asynchronous function and applies both sync and async modifiers.

        Raises:
            TypeError: If the wrapped function is already asynchronous.

        Returns:
            The asynchronous version of the wrapped function.

        See Also:
            - :meth:`_asyncify`
        """
        if self._async_def:
            raise TypeError(
                f"Can only be applied to sync functions, not {self.__wrapped__}"
            )
        return self._asyncify(self._modified_fn)  # type: ignore [arg-type]

    @functools.cached_property
    def _modified_fn(self) -> AnyFn[P, T]:
        """
        Applies modifiers to the wrapped function.

        If the wrapped function is an asynchronous function, this method applies async modifiers.
        If the wrapped function is a synchronous function, this method applies sync modifiers.

        Returns:
            The modified function.

        See Also:
            - :meth:`ModifierManager.apply_async_modifiers`
            - :meth:`ModifierManager.apply_sync_modifiers`
        """
        if self._async_def:
            return self.modifiers.apply_async_modifiers(self.__wrapped__)  # type: ignore [arg-type]
        return self.modifiers.apply_sync_modifiers(self.__wrapped__)  # type: ignore [return-value]

    @functools.cached_property
    def _async_wrap(self):  # -> SyncFn[[CoroFn[P, T]], MaybeAwaitable[T]]:
        """
        The final wrapper if the wrapped function is an asynchronous function.

        This method applies the appropriate modifiers and determines whether to await the result.

        Returns:
            The wrapped function with async handling.

        See Also:
            - :meth:`_run_sync`
            - :meth:`_await`
        """

        modified_fn = self._modified_fn
        await_helper = self._await

        @functools.wraps(modified_fn)
        def async_wrap(*args: P.args, **kwargs: P.kwargs) -> MaybeAwaitable[T]:  # type: ignore [name-defined]
            # sourcery skip: assign-if-exp
            # we dont want this so profiler outputs are more useful

            # Must take place before coro is created, we're popping a kwarg.
            should_await = self._run_sync(kwargs)
            coro = modified_fn(*args, **kwargs)
            if should_await:
                return await_helper(coro)
            else:
                return coro

        return async_wrap

    @functools.cached_property
    def _sync_wrap(self):  # -> SyncFn[[SyncFn[P, T]], MaybeAwaitable[T]]:
        """
        The final wrapper if the wrapped function is a synchronous function.

        This method applies the appropriate modifiers and determines whether to run the function synchronously or asynchronously.

        Returns:
            The wrapped function with sync handling.

        See Also:
            - :meth:`_run_sync`
            - :meth:`_asyncified`
        """

        modified_fn = self._modified_fn
        asyncified = self._asyncified

        @functools.wraps(modified_fn)
        def sync_wrap(*args: P.args, **kwargs: P.kwargs) -> MaybeAwaitable[T]:  # type: ignore [name-defined]
            if self._run_sync(kwargs):
                return modified_fn(*args, **kwargs)
            return asyncified(*args, **kwargs)

        return sync_wrap

    __docstring_append__ = ":class:`~a_sync.a_sync.function.ASyncFunction`, you can optionally pass either a `sync` or `asynchronous` kwarg with a boolean value."


if sys.version_info < (3, 10):
    _inherit = ASyncFunction[AnyFn[P, T], ASyncFunction[P, T]]
else:
    _inherit = ASyncFunction[[AnyFn[P, T]], ASyncFunction[P, T]]


class ASyncDecorator(_ModifiedMixin):
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
        assert "default" in modifiers, modifiers
        self.modifiers = ModifierManager(modifiers)
        self.validate_inputs()

    def validate_inputs(self) -> None:
        """
        Validates the input modifiers.

        Raises:
            ValueError: If 'default' is not 'sync', 'async', or None.

        See Also:
            - :attr:`ModifierManager.default`
        """
        if self.modifiers.default not in ["sync", "async", None]:
            raise ValueError(
                f"'default' must be either 'sync', 'async', or None. You passed {self.modifiers.default}."
            )

    @overload
    def __call__(self, func: AnyFn[Concatenate[B, P], T]) -> "ASyncBoundMethod[B, P, T]":  # type: ignore [override]
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
    def __call__(self, func: AnyFn[P, T]) -> ASyncFunction[P, T]:  # type: ignore [override]
        """
        Decorates a function with async or sync behavior based on the default modifier.

        Args:
            func: The function to decorate.

        Returns:
            An ASyncFunction instance with the appropriate default behavior.

        See Also:
            - :class:`ASyncFunction`
        """

    def __call__(self, func: AnyFn[P, T]) -> ASyncFunction[P, T]:  # type: ignore [override]
        """
        Decorates a function with async or sync behavior based on the default modifier.

        Args:
            func: The function to decorate.

        Returns:
            An ASyncFunction instance with the appropriate default behavior.

        See Also:
            - :class:`ASyncFunction`
        """
        if self.default == "async":
            return ASyncFunctionAsyncDefault(func, **self.modifiers)
        elif self.default == "sync":
            return ASyncFunctionSyncDefault(func, **self.modifiers)
        elif asyncio.iscoroutinefunction(func):
            return ASyncFunctionAsyncDefault(func, **self.modifiers)
        else:
            return ASyncFunctionSyncDefault(func, **self.modifiers)


def _check_not_genfunc(func: Callable) -> None:
    """Raises an error if the function is a generator or async generator.

    Args:
        func: The function to check.

    Raises:
        ValueError: If the function is a generator or async generator.

    See Also:
        - :func:`inspect.isasyncgenfunction`
        - :func:`inspect.isgeneratorfunction`
    """
    if inspect.isasyncgenfunction(func) or inspect.isgeneratorfunction(func):
        raise ValueError("unable to decorate generator functions with this decorator")


# Mypy helper classes


class ASyncFunctionSyncDefault(ASyncFunction[P, T]):
    """A specialized :class:`~ASyncFunction` that defaults to synchronous execution.

    This class is used when the :func:`~a_sync` decorator is applied with `default='sync'`.
    It provides type hints to indicate that the default call behavior is synchronous and
    supports IDE type checking for most use cases.

    The wrapped function can still be called asynchronously by passing `sync=False`
    or `asynchronous=True` as a keyword argument.

    Example:
        @a_sync(default='sync')
        async def my_function(x: int) -> str:
            return str(x)

        # Synchronous call (default behavior)
        result = my_function(5)  # returns "5"

        # Asynchronous call
        result = await my_function(5, sync=False)  # returns "5"
    """

    @overload
    def __call__(self, *args: P.args, sync: Literal[True], **kwargs: P.kwargs) -> T:
        # TODO write specific docs for this overload
        ...

    @overload
    def __call__(
        self, *args: P.args, sync: Literal[False], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]:
        # TODO write specific docs for this overload
        ...

    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs
    ) -> T:
        # TODO write specific docs for this overload
        ...

    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[True], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]:
        # TODO write specific docs for this overload
        ...

    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        # TODO write specific docs for this overload
        ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MaybeCoro[T]:
        """Calls the wrapped function, defaulting to synchronous execution.

        This method overrides the base :meth:`ASyncFunction.__call__` to provide a synchronous
        default behavior.

        Args:
            *args: Positional arguments to pass to the wrapped function.
            **kwargs: Keyword arguments to pass to the wrapped function.

        Raises:
            Exception: Any exception that may be raised by the wrapped function.

        Returns:
            The result of the function call.

        See Also:
            - :meth:`ASyncFunction.__call__`
        """
        return self.fn(*args, **kwargs)

    __docstring_append__ = ":class:`~a_sync.a_sync.function.ASyncFunctionSyncDefault`, you can optionally pass `sync=False` or `asynchronous=True` to force it to return a coroutine. Without either kwarg, it will run synchronously."


class ASyncFunctionAsyncDefault(ASyncFunction[P, T]):
    """
    A specialized :class:`~ASyncFunction` that defaults to asynchronous execution.

    This class is used when the :func:`~a_sync` decorator is applied with `default='async'`.
    It provides type hints to indicate that the default call behavior is asynchronous
    and supports IDE type checking for most use cases.

    The wrapped function can still be called synchronously by passing `sync=True`
    or `asynchronous=False` as a keyword argument.

    Example:
        @a_sync(default='async')
        async def my_function(x: int) -> str:
            return str(x)

        # Asynchronous call (default behavior)
        result = await my_function(5)  # returns "5"

        # Synchronous call
        result = my_function(5, sync=True)  # returns "5"
    """

    @overload
    def __call__(self, *args: P.args, sync: Literal[True], **kwargs: P.kwargs) -> T:
        # TODO write specific docs for this overload
        ...

    @overload
    def __call__(
        self, *args: P.args, sync: Literal[False], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]:
        # TODO write specific docs for this overload
        ...

    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs
    ) -> T:
        # TODO write specific docs for this overload
        ...

    @overload
    def __call__(
        self, *args: P.args, asynchronous: Literal[True], **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T]:
        # TODO write specific docs for this overload
        ...

    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Coroutine[Any, Any, T]: ...
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MaybeCoro[T]:
        """Calls the wrapped function, defaulting to asynchronous execution.

        This method overrides the base :meth:`ASyncFunction.__call__` to provide an asynchronous
        default behavior.

        Args:
            *args: Positional arguments to pass to the wrapped function.
            **kwargs: Keyword arguments to pass to the wrapped function.

        Raises:
            Exception: Any exception that may be raised by the wrapped function.

        Returns:
            The result of the function call.

        See Also:
            - :meth:`ASyncFunction.__call__`
        """
        return self.fn(*args, **kwargs)

    __docstring_append__ = ":class:`~a_sync.a_sync.function.ASyncFunctionAsyncDefault`, you can optionally pass `sync=True` or `asynchronous=False` to force it to run synchronously and return a value. Without either kwarg, it will return a coroutine for you to await."


class ASyncDecoratorSyncDefault(ASyncDecorator):
    @overload
    def __call__(self, func: AnyFn[Concatenate[B, P], T]) -> "ASyncBoundMethodSyncDefault[P, T]":  # type: ignore [override]
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
    def __call__(self, func: AnyBoundMethod[P, T]) -> ASyncFunctionSyncDefault[P, T]:  # type: ignore [override]
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
    def __call__(self, func: AnyFn[P, T]) -> ASyncFunctionSyncDefault[P, T]:  # type: ignore [override]
        """
        Decorates a function with synchronous default behavior.

        Args:
            func: The function to decorate.

        Returns:
            An ASyncFunctionSyncDefault instance with synchronous default behavior.

        See Also:
            - :class:`ASyncFunctionSyncDefault`
        """

    def __call__(self, func: AnyFn[P, T]) -> ASyncFunctionSyncDefault[P, T]:
        # TODO write specific docs for this implementation
        return ASyncFunctionSyncDefault(func, **self.modifiers)


class ASyncDecoratorAsyncDefault(ASyncDecorator):
    @overload
    def __call__(self, func: AnyFn[Concatenate[B, P], T]) -> "ASyncBoundMethodAsyncDefault[P, T]":  # type: ignore [override]
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
    def __call__(self, func: AnyBoundMethod[P, T]) -> ASyncFunctionAsyncDefault[P, T]:  # type: ignore [override]
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
    def __call__(self, func: AnyFn[P, T]) -> ASyncFunctionAsyncDefault[P, T]:  # type: ignore [override]
        """
        Decorates a function with asynchronous default behavior.

        Args:
            func: The function to decorate.

        Returns:
            An ASyncFunctionAsyncDefault instance with asynchronous default behavior.

        See Also:
            - :class:`ASyncFunctionAsyncDefault`
        """

    def __call__(self, func: AnyFn[P, T]) -> ASyncFunctionAsyncDefault[P, T]:
        # TODO write specific docs for this implementation
        return ASyncFunctionAsyncDefault(func, **self.modifiers)
