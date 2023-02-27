
import functools
from typing import Callable, Coroutine, Literal, TypeVar, overload

from typing_extensions import ParamSpec  # type: ignore

from a_sync import _flags, _helpers, _kwargs, exceptions

P = ParamSpec("P")
T = TypeVar("T")


@overload # no args
def a_sync(default: Callable[P, T] = None) -> Callable[P, T]:...

@overload # both defs, None default
def a_sync(default: Literal[None] = None) -> Callable[[Callable[P, T]], Callable[P, T]]:...

@overload # async def, async default
def a_sync(default: Literal['async'] = None) -> Callable[[Callable[P, Coroutine[None, None, T]]], Callable[P, Coroutine[None, None, T]]]:...

@overload # sync def, async default  TODO: DOESN'T TYPE CHECK CORRECTLY, FIX
def a_sync(default: Literal['async'] = None) -> Callable[[Callable[P, T]], Callable[P, Coroutine[None, None, T]]]:...

@overload # async def, sync default
def a_sync(default: Literal['sync'] = None) -> Callable[[Callable[P, Coroutine[None, None, T]]], Callable[P, T]]:...

@overload # sync def, sync default  TODO: DOESN'T TYPE CHECK CORRECTLY, FIX
def a_sync(default: Literal['sync'] = None) -> Callable[[Callable[P, T]], Callable[P, T]]:...

def a_sync(default = None):
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
    if default not in ['async', 'sync', None]:
        if callable(default):
            """
            This code will run if the a_sync decorator is applied to a function without args, like so:
    
            @a_sync
            async def some_fn():
                await asyncio.sleep(1)
                return
            
            It is equivalent to this:
            
            @a_sync(default=None)
            async def some_fn():
                await asyncio.sleep(1)
                return
            """
            return a_sync(default=None)(default)
        raise ValueError(f"'default' must be either 'sync', 'async', or None. You passed {default}.")
    
    def a_sync_deco(coro_fn: Callable[P, T]) -> Callable[P, T]:  # type: ignore
        _helpers._validate_wrapped_fn(coro_fn)
        @functools.wraps(coro_fn)
        def a_sync_wrap(*args: P.args, **kwargs: P.kwargs) -> T:  # type: ignore
            # If a flag was specified in the kwargs, we will defer to it.
            try:
                should_await = _kwargs.is_sync(kwargs, pop_flag=True)
            except exceptions.NoFlagsFound:
                # No flag specified in the kwargs, we will defer to 'default'.
                should_await = True if default == 'sync' else False
            return _helpers._await_if_sync(coro_fn(*args, **kwargs), should_await)
        return a_sync_wrap
    return a_sync_deco
