import asyncio
import inspect
import sys
import typing
from contextlib import contextmanager
from logging import ERROR, getLogger
from libc.stdint cimport uintptr_t

import async_lru
import async_property
from typing_extensions import Unpack

from a_sync._typing import AnyFn, AnyIterable, CoroFn, DefaultMode, MaybeCoro, ModifierKwargs, P, SyncFn, T
from a_sync.a_sync._kwargs cimport get_flag_name, is_sync
from a_sync.a_sync._helpers cimport _asyncify, _await
from a_sync.a_sync.flags cimport VIABLE_FLAGS
from a_sync.a_sync.modifiers cimport ModifierManager
from a_sync.functools cimport update_wrapper, wraps

if typing.TYPE_CHECKING:
    from a_sync import TaskMapping
    from a_sync.a_sync.method import (
        ASyncBoundMethod,
        ASyncBoundMethodAsyncDefault,
        ASyncBoundMethodSyncDefault,
    )

else:
    # due to circ import issues we will populate this later
    TaskMapping = None


ctypedef object object_id


# cdef asyncio
cdef object iscoroutinefunction = asyncio.iscoroutinefunction
del asyncio

# cdef inspect
cdef object getargspec
if sys.version_info < (3, 11):
    getargspec = inspect.getargspec
else:
    # getargspec was deprecated in python 3.11
    getargspec = inspect.getfullargspec
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

    cdef inline object _asyncify(self, func: SyncFn[P, T]):
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
    
    cdef inline object get_await(self):
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
    
    cdef inline str get_default(self):
        cdef str default = self.__default
        if default is None:
            default = self.modifiers.get_default()
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

cdef set[object_id] _argspec_validated = set()

cdef inline void _validate_argspec_cached(fn: Callable):
    cdef object_id fid = id(fn)
    if fid not in _argspec_validated:
        _validate_argspec(fn)
        _argspec_validated.add(fid)

cdef inline void _validate_argspec(fn: Callable):
    cdef tuple[str, ...] fn_args
    cdef object fn_code
    
    try:
        fn_code = fn.__code__  # May fail for built-ins or special callables
        fn_args = fn_code.co_varnames[:fn_code.co_argcount]
    except:
        try:
            argspec = getargspec(fn)
        except TypeError:
            warn = logger.warning
            warn(f"inspect.{getargspec.__name__} does not support {fn}")
            warn("we will allow you to proceed but cannot guarantee things will work")
            warn("hopefully you know what you're doing...")
            return
        else:
            # python argspec is already a tuple but mypyc compiled functions
            # return a list which me must coerce to tuple.
            fn_args = tuple(argspec[0])
    
    for flag in fn_args:
        if flag in VIABLE_FLAGS:
            raise RuntimeError(
                f"{fn} must not have any arguments with the following names: {VIABLE_FLAGS}"
            )

    
# ... content unchanged ...

cdef inline void _import_TaskMapping():
    global TaskMapping
    from a_sync import TaskMapping


@contextmanager
def im_a_fuckin_pro_dont_worry() -> typing.Iterator[None]:
    """
    This context manager allows you to confirm to ez-a-sync that you know what you are doing, 
    to prevent the emission of the following logs:

    ```
    WARNING:a_sync.a_sync.function:inspect.getfullargspec does not support <your_lib.your_cls object at 0x7f93130c8180>
    WARNING:a_sync.a_sync.function:we will allow you to proceed but cannot guarantee things will work
    WARNING:a_sync.a_sync.function:hopefully you know what you're doing...
    ```
    """
    original_level = logger.level
    logger.setLevel(ERROR)
    try:
        yield
    finally:
        logger.setLevel(original_level)
