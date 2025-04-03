import asyncio
import functools
import inspect
import sys
import typing
from logging import getLogger
from libc.stdint cimport uintptr_t

import async_lru
import async_property
from typing_extensions import Unpack

from a_sync._typing import AnyFn, AnyIterable, CoroFn, DefaultMode, MaybeCoro, ModifierKwargs, P, SyncFn, T
from a_sync.a_sync._kwargs cimport get_flag_name, is_sync
from a_sync.a_sync._helpers cimport _asyncify, _await
from a_sync.a_sync.flags cimport VIABLE_FLAGS
from a_sync.a_sync.modifiers cimport ModifierManager
from a_sync.functools cimport cached_property_unsafe, update_wrapper, wraps
if typing.TYPE_CHECKING:
    from a_sync import TaskMapping
    from a_sync.a_sync.method import (
        ASyncBoundMethod,
        ASyncBoundMethodAsyncDefault,
        ASyncBoundMethodSyncDefault,
    )


# cdef asyncio
cdef object iscoroutinefunction = asyncio.iscoroutinefunction
del asyncio

# cdef functools
cdef object cached_property = functools.cached_property
del functools

# cdef inspect
cdef object getfullargspec = inspect.getfullargspec
cdef object isasyncgenfunction = inspect.isasyncgenfunction
cdef object isgeneratorfunction = inspect.isgeneratorfunction
del inspect

# cdef logging
cdef public object logger = getLogger(__name__)
cdef object _logger_debug = logger.debug

# cdef typing
cdef object TYPE_CHECKING = typing.TYPE_CHECKING
cdef object Any = typing.Any
cdef object Callable = typing.Callable
cdef object Coroutine = typing.Coroutine
cdef object Generic = typing.Generic
cdef object Literal = typing.Literal
cdef object Optional = typing.Optional
cdef object overload = typing.overload


# cdef async_lru
cdef object _LRUCacheWrapper = async_lru._LRUCacheWrapper

# cdef async_property
cdef object AsyncPropertyDescriptor = async_property.base.AsyncPropertyDescriptor
cdef object AsyncCachedPropertyDescriptor = async_property.cached.AsyncCachedPropertyDescriptor


cdef class _ModifiedMixin:
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

    @property
    def default(self) -> DefaultMode:
        """
        Gets the default execution mode (sync, async, or None) for the function.

        Returns:
            The default execution mode.

        See Also:
            - :attr:`ModifierManager.default`
        """
        return self.get_default()

    cdef object _asyncify(self, func: SyncFn[P, T]):
        """
        Converts a synchronous function to an asynchronous one and applies async modifiers.

        Args:
            func: The synchronous function to be converted.

        Returns:
            The asynchronous version of the function with applied modifiers.

        See Also:
            - :meth:`ModifierManager.apply_async_modifiers`
        """
        return self.modifiers.apply_async_modifiers(_asyncify(func, self.modifiers.executor))
    
    cdef object get_await(self):
        """
        Applies sync modifiers to the _helpers._await function and caches it.

        Returns:
            The modified _await function.

        See Also:
            - :meth:`ModifierManager.apply_sync_modifiers`
        """
        awaiter = self.__await
        if awaiter is None:
            awaiter = self.modifiers.apply_sync_modifiers(_await)
            self.__await = awaiter
        return awaiter
    
    cdef str get_default(self):
        default = self.__default
        if default is None:
            default = self.modifiers.default
            self.__default = default
        return default



cdef void _validate_wrapped_fn(fn: Callable):
    """Ensures 'fn' is an appropriate function for wrapping with a_sync.

    Args:
        fn: The function to validate.

    Raises:
        TypeError: If the input is not callable.
        RuntimeError: If the function has arguments with names that conflict with viable flags.

    See Also:
        - :func:`_check_not_genfunc`
    """
    typ = type(fn)
    if typ is _function_type:
        _check_not_genfunc_cached(fn)
        _validate_argspec_cached(fn)
        return
    if issubclass(typ, (AsyncPropertyDescriptor, AsyncCachedPropertyDescriptor)):
        return  # These are always valid
    elif issubclass(typ, _LRUCacheWrapper):
        fn = fn.__wrapped__
        if type(fn) is _function_type:
            _check_not_genfunc_cached(fn)
            _validate_argspec_cached(fn)
            return
    elif not callable(fn):
        raise TypeError(f"Input is not callable. Unable to decorate {fn}")
    _check_not_genfunc(fn)
    _validate_argspec(fn)

cdef object _function_type = type(getLogger)

cdef set[uintptr_t] _argspec_validated = set()

cdef void _validate_argspec_cached(fn: Callable):
    cdef uintptr_t fid = id(fn)
    if fid not in _argspec_validated:
        _validate_argspec(fn)
        _argspec_validated.add(fid)

cdef void _validate_argspec(fn: Callable):
    fn_args = getfullargspec(fn)[0]
    for flag in VIABLE_FLAGS:
        if flag in fn_args:
            raise RuntimeError(
                f"{fn} must not have any arguments with the following names: {VIABLE_FLAGS}"
            )

cdef inline bint _run_sync(object function, dict kwargs):
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
    """
    cdef str flag = get_flag_name(kwargs)
    if flag:
        # If a flag was specified in the kwargs, we will defer to it.
        return is_sync(flag, kwargs, pop_flag=True)
    else:
        # No flag specified in the kwargs, we will defer to 'default'.
        return function._sync_default
    
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

    _fn = None

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
        _ModifiedMixin self,
        fn: AnyFn[P, T],
        _skip_validate: bint = False,
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

        update_wrapper(self, fn)
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
        _logger_debug(
            "calling %s fn: %s with args: %s kwargs: %s", self, self.fn, args, kwargs
        )
        return self.fn(*args, **kwargs)

    def __repr__(self) -> str:
        return "<{} {}.{} at {}>".format(
            self.__class__.__name__, self.__module__, self.__name__, hex(id(self))
        )

    @property
    def fn(self):
        # NOTE type hint doesnt work in py3.8 or py3.9, debug later
        #  -> Union[SyncFn[[CoroFn[P, T]], MaybeAwaitable[T]], SyncFn[[SyncFn[P, T]], MaybeAwaitable[T]]]:
        """
        Returns the final wrapped version of :attr:`ASyncFunction.__wrapped__` decorated with all of the a_sync goodness.

        Returns:
            The final wrapped function.

        See Also:
            - :meth:`_async_wrap`
            - :meth:`_sync_wrap`
        """
        fn = self._fn
        if fn is None:
            fn = self._async_wrap if self._async_def else self._sync_wrap
            self._fn = fn
        return fn

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
        ) -> bint:
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
        ) -> bint:
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
        ) -> bint:
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
        ) -> bint:
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

    @cached_property_unsafe
    def _sync_default(self) -> bint:
        """
        Determines the default execution mode (sync or async) for the function.

        If the user did not specify a default, this method defers to the function's
        definition (sync vs async def).

        Returns:
            True if the default is sync, False if async.

        See Also:
            - :attr:`default`
        """
        cdef str default = _ModifiedMixin.get_default(self)
        return (
            True
            if default == "sync"
            else False if default == "async" else not self._async_def
        )

    @cached_property_unsafe
    def _async_def(self) -> bint:
        """
        Checks if the wrapped function is an asynchronous function.

        Returns:
            True if the function is asynchronous, otherwise False.

        See Also:
            - :func:`asyncio.iscoroutinefunction`
        """
        return iscoroutinefunction(self.__wrapped__)

    @cached_property_unsafe
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
        return _ModifiedMixin._asyncify(self, self._modified_fn)  # type: ignore [arg-type]

    @cached_property
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

    @cached_property
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
        await_helper = _ModifiedMixin.get_await(self)

        @wraps(modified_fn)
        def async_wrap(*args: P.args, **kwargs: P.kwargs) -> MaybeAwaitable[T]:  # type: ignore [name-defined]
            # sourcery skip: assign-if-exp
            # we dont want this so profiler outputs are more useful

            # Must take place before coro is created, we're popping a kwarg.
            should_await = _run_sync(self, kwargs)
            coro = modified_fn(*args, **kwargs)
            if should_await:
                return await_helper(coro)
            else:
                return coro

        return async_wrap

    @cached_property
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

        @wraps(modified_fn)
        def sync_wrap(*args: P.args, **kwargs: P.kwargs) -> MaybeAwaitable[T]:  # type: ignore [name-defined]
            if _run_sync(self, kwargs):
                return modified_fn(*args, **kwargs)
            return asyncified(*args, **kwargs)

        return sync_wrap

    __docstring_append__ = ":class:`~a_sync.a_sync.function.ASyncFunction`, you can optionally pass either a `sync` or `asynchronous` kwarg with a boolean value."


if sys.version_info < (3, 10):
    _inherit = ASyncFunction[AnyFn[P, T], ASyncFunction[P, T]]
else:
    _inherit = ASyncFunction[[AnyFn[P, T]], ASyncFunction[P, T]]


cdef class ASyncDecorator(_ModifiedMixin):
    def __cinit__(self, **modifiers: Unpack[ModifierKwargs]) -> None:
        """
        Initializes an ASyncDecorator instance by validating the inputs.

        Args:
            **modifiers: Keyword arguments for function modifiers.

        Raises:
            ValueError: If 'default' is not 'sync', 'async', or None.

        See Also:
            - :class:`ModifierManager`
        """
        if modifiers.get("default", object) not in ("sync", "async", None):
            if "default" not in modifiers:
                raise ValueError("you must pass a value for `default`")
            raise ValueError(
                f"'default' must be either 'sync', 'async', or None. You passed {modifiers['default']}."
            )
        self.modifiers = ModifierManager(modifiers)

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
        cdef str default = self.get_default()
        if default == "async":
            return ASyncFunctionAsyncDefault(func, **self.modifiers._modifiers)
        elif default == "sync":
            return ASyncFunctionSyncDefault(func, **self.modifiers._modifiers)
        elif iscoroutinefunction(func):
            return ASyncFunctionAsyncDefault(func, **self.modifiers._modifiers)
        else:
            return ASyncFunctionSyncDefault(func, **self.modifiers._modifiers)


cdef set[uintptr_t] _is_genfunc_cache = set()

cdef void _check_not_genfunc_cached(func: Callable):
    cdef uintptr_t fid = id(func)
    if fid not in _is_genfunc_cache:
        _check_not_genfunc(func)
        _is_genfunc_cache.add(fid)

cdef void _check_not_genfunc(func: Callable):
    """Raises an error if the function is a generator or async generator.

    Args:
        func: The function to check.

    Raises:
        ValueError: If the function is a generator or async generator.

    See Also:
        - :func:`inspect.isasyncgenfunction`
        - :func:`inspect.isgeneratorfunction`
    """
    if isasyncgenfunction(func) or isgeneratorfunction(func):
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


cdef class ASyncDecoratorSyncDefault(ASyncDecorator):
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
        return ASyncFunctionSyncDefault(func, **self.modifiers._modifiers)


cdef class ASyncDecoratorAsyncDefault(ASyncDecorator):
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
        return ASyncFunctionAsyncDefault(func, **self.modifiers._modifiers)
