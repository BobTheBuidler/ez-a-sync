
import functools
from typing import (Awaitable, Callable, Literal, Optional, TypeVar, Union,
                    overload)

from typing_extensions import ParamSpec  # type: ignore [attr-defined]

from a_sync import _flags, _helpers, _kwargs, exceptions

P = ParamSpec("P")
T = TypeVar("T")

########################
# The a_sync decorator #
########################

# @a_sync
# def some_fn():
#     pass
#
# @a_sync
# async def some_fn():
#     pass

@overload # async def, None default
def a_sync(
    coro_fn: Callable[P, Awaitable[T]] = None,  # type: ignore [misc]
    default: Literal[None] = None
) -> Callable[P, Awaitable[T]]:...  # type: ignore [misc]

@overload # sync def none default
def a_sync(  # type: ignore [misc]
    coro_fn: Callable[P, T] = None,  # type: ignore [misc]
    default: Literal[None] = None
) -> Callable[P, T]:...  # type: ignore [misc]

# @a_sync(default='async')
# def some_fn():
#     pass
#
# @a_sync(default='async')
# async def some_fn():
#     pass
#
# NOTE These should output a decorator that will be applied to 'some_fn'

@overload 
def a_sync(
    coro_fn: Literal[None] = None,
    default: Literal['async'] = None,
) -> Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, Awaitable[T]]]:...  # type: ignore [misc]

@overload # if you try to use default as the only arg
def a_sync(
    coro_fn: Literal['async'] = None,
    default: Literal[None] = None,
) -> Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, Awaitable[T]]]:...  # type: ignore [misc]

# @a_sync(default='sync')
# def some_fn():
#     pass
#
# @a_sync(default='sync')
# async def some_fn():
#     pass
#
# NOTE These should output a decorator that will be applied to 'some_fn'

@overload 
def a_sync(
    coro_fn: Literal[None] = None,
    default: Literal['sync'] = None,
) -> Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, T]]:...  # type: ignore [misc]

@overload # if you try to use default as the only arg
def a_sync(
    coro_fn: Literal['sync'] = None,
    default: Literal[None] = None,
) -> Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, T]]:...  # type: ignore [misc]

# catchall
def a_sync(
    coro_fn: Optional[Union[Callable[P, Awaitable[T]], Callable[P, T]]] = None,  # type: ignore [misc]
    default: Literal['sync', 'async', None] = None,
) -> Union[  # type: ignore [misc]
    # sync coro_fn, default=None
    Callable[P, T],
    # async coro_fn, default=None
    Callable[P, Awaitable[T]],
    # coro_fn=None, default='async'
    Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, Awaitable[T]]],
    # coro_fn=None, default='sync'
    Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, T]],
]:
    f"""
    A coroutine function decorated with this decorator can be called as a sync function by passing a boolean value for any of these kwargs: {_flags.VIABLE_FLAGS}

    ######################
    # async def examples #
    ######################

    @a_sync
    async def some_fn():
        reurn True
    
    await some_fn() == True
    some_fn(sync=True) == True

    
    @a_sync(default=None)
    async def some_fn():
        reurn True
    
    await some_fn() == True
    some_fn(sync=True) == True

    
    @a_sync(default='async')
    async def some_fn():
        reurn True
    
    await some_fn() == True
    some_fn(sync=True) == True
    

    @a_sync(default='sync')
    async def some_fn():
        reurn True
    
    some_fn() == True
    await some_fn(sync=False) == True

    
    # TODO: in a future release, I will make this usable with sync functions as well

    ################
    # def examples #
    ################

    @a_sync
    def some_fn():
        reurn True
    
    some_fn() == True
    await some_fn(sync=False) == True
    

    @a_sync(default=None)
    def some_fn():
        reurn True
    
    some_fn() == True
    await some_fn(sync=False) == True


    @a_sync(default='async')
    def some_fn():
        reurn True
    
    await some_fn() == True
    some_fn(sync=True) == True


    @a_sync(default='sync')
    def some_fn():
        reurn True
    
    some_fn() == True
    await some_fn(sync=False) == True
    """
    
    if coro_fn in ['async', 'sync']:
        # If the dev tried passing a default as an arg instead of a kwarg:
        default = coro_fn
        coro_fn = None
        
    if default not in ['async', 'sync', None]:
        raise ValueError(f"'default' must be either 'sync', 'async', or None. You passed {default}.")
    
    def a_sync_deco(coro_fn: Callable[P, Awaitable[T]]) -> Union[Callable[P, Awaitable[T]], Callable[P, T]]:  # type: ignore [misc]
        _helpers._validate_wrapped_fn(coro_fn)
        @functools.wraps(coro_fn)
        def a_sync_wrap(*args: P.args, **kwargs: P.kwargs) -> Union[Awaitable[T], T]:  # type: ignore [name-defined]
            # If a flag was specified in the kwargs, we will defer to it.
            try:
                should_await = _kwargs.is_sync(kwargs, pop_flag=True)
            except exceptions.NoFlagsFound:
                # No flag specified in the kwargs, we will defer to 'default'.
                should_await = True if default == 'sync' else False
            return _helpers._await_if_sync(coro_fn(*args, **kwargs), should_await)  # type: ignore [call-overload]
        return a_sync_wrap
    
    if coro_fn is None:
        return a_sync_deco
    if not callable(coro_fn):
        raise RuntimeError(f"a_sync's first arg must be callable. You passed {coro_fn}.")
    return a_sync_deco(coro_fn)
