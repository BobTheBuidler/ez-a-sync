# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc
import asyncio
import functools

from a_sync import exceptions, primitives
from a_sync._typing import *

# We keep this here for now so we don't break downstream deps. Eventually will be removed.
from a_sync.primitives import ThreadsafeSemaphore, DummySemaphore


@overload
def apply_semaphore(  # type: ignore [misc]
    semaphore: SemaphoreSpec,
) -> AsyncDecorator[P, T]:
    """Applies a semaphore to a coroutine function.

    This overload is used when the semaphore is provided as a single argument,
    returning a decorator that can be applied to a coroutine function.

    Args:
        semaphore: The semaphore to apply, which can be an integer or an asyncio.Semaphore object.
    """


@overload
def apply_semaphore(
    coro_fn: CoroFn[P, T],
    semaphore: SemaphoreSpec,
) -> CoroFn[P, T]:
    """Applies a semaphore to a coroutine function.

    This overload is used when both the coroutine function and semaphore are provided,
    directly applying the semaphore to the coroutine function.

    Args:
        coro_fn: The coroutine function to which the semaphore will be applied.
        semaphore: The semaphore to apply, which can be an integer or an asyncio.Semaphore object.
    """


def apply_semaphore(
    coro_fn: Optional[Union[CoroFn[P, T], SemaphoreSpec]] = None,
    semaphore: SemaphoreSpec = None,
) -> AsyncDecoratorOrCoroFn[P, T]:
    """Applies a semaphore to a coroutine function or returns a decorator.

    This function can be used to apply a semaphore to a coroutine function either by
    passing the coroutine function and semaphore as arguments or by using the semaphore
    as a decorator. It raises exceptions if the inputs are not valid.

    Args:
        coro_fn: The coroutine function to which the semaphore will be applied, or None
            if the semaphore is to be used as a decorator.
        semaphore: The semaphore to apply, which can be an integer or an asyncio.Semaphore object.

    Raises:
        ValueError: If both coro_fn and semaphore are provided as invalid inputs.
        exceptions.FunctionNotAsync: If the provided function is not a coroutine.
        TypeError: If the semaphore is not an integer or an asyncio.Semaphore object.
    """
    # Parse Inputs
    if isinstance(coro_fn, (int, asyncio.Semaphore)):
        if semaphore is not None:
            raise ValueError("You can only pass in one arg.")
        semaphore = coro_fn
        coro_fn = None

    elif not asyncio.iscoroutinefunction(coro_fn):
        raise exceptions.FunctionNotAsync(coro_fn)

    # Create the semaphore if necessary
    if isinstance(semaphore, int):
        semaphore = primitives.ThreadsafeSemaphore(semaphore)
    elif not isinstance(semaphore, asyncio.Semaphore):
        raise TypeError(
            f"'semaphore' must either be an integer or a Semaphore object. You passed {semaphore}"
        )

    # Create and return the decorator
    if isinstance(semaphore, primitives.Semaphore):
        # NOTE: Our `Semaphore` primitive can be used as a decorator.
        #       While you can use it the `async with` way like any other semaphore and we could make this code section cleaner,
        #       applying it as a decorator adds some useful info to its debug logs so we do that here if we can.
        semaphore_decorator = semaphore

    else:

        def semaphore_decorator(coro_fn: CoroFn[P, T]) -> CoroFn[P, T]:
            @functools.wraps(coro_fn)
            async def semaphore_wrap(*args, **kwargs) -> T:
                async with semaphore:  # type: ignore [union-attr]
                    return await coro_fn(*args, **kwargs)

            return semaphore_wrap

    return semaphore_decorator if coro_fn is None else semaphore_decorator(coro_fn)


dummy_semaphore = primitives.DummySemaphore()
"""A dummy semaphore that does not enforce any concurrency limits."""
