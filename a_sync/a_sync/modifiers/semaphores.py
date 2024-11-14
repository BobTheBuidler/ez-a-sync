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
    """Create a decorator to apply a semaphore to a coroutine function.

    This overload is used when the semaphore is provided as a single argument,
    returning a decorator that can be applied to a coroutine function.

    Args:
        semaphore (Union[int, asyncio.Semaphore, primitives.Semaphore]):
            The semaphore to apply, which can be an integer, an `asyncio.Semaphore`, or a `primitives.Semaphore`.

    Examples:
        Using as a decorator with an integer semaphore:
        >>> @apply_semaphore(2)
        ... async def limited_concurrent_function():
        ...     pass

        Using as a decorator with an `asyncio.Semaphore`:
        >>> sem = asyncio.Semaphore(2)
        >>> @apply_semaphore(sem)
        ... async def another_function():
        ...     pass

        Using as a decorator with a `primitives.Semaphore`:
        >>> sem = primitives.ThreadsafeSemaphore(2)
        >>> @apply_semaphore(sem)
        ... async def yet_another_function():
        ...     pass

    See Also:
        - :class:`asyncio.Semaphore`
        - :class:`primitives.Semaphore`

    Note:
        `primitives.Semaphore` is a subclass of `asyncio.Semaphore`. Therefore, when the documentation refers to `asyncio.Semaphore`, it also includes `primitives.Semaphore` and any other subclasses.
    """


@overload
def apply_semaphore(
    coro_fn: CoroFn[P, T],
    semaphore: SemaphoreSpec,
) -> CoroFn[P, T]:
    """Apply a semaphore directly to a coroutine function.

    This overload is used when both the coroutine function and semaphore are provided,
    directly applying the semaphore to the coroutine function.

    Args:
        coro_fn (Callable): The coroutine function to which the semaphore will be applied.
        semaphore (Union[int, asyncio.Semaphore, primitives.Semaphore]):
            The semaphore to apply, which can be an integer, an `asyncio.Semaphore`, or a `primitives.Semaphore`.

    Examples:
        Applying directly to a function with an integer semaphore:
        >>> async def my_coroutine():
        ...     pass
        >>> my_coroutine = apply_semaphore(my_coroutine, 3)

        Applying directly with an `asyncio.Semaphore`:
        >>> sem = asyncio.Semaphore(3)
        >>> my_coroutine = apply_semaphore(my_coroutine, sem)

        Applying directly with a `primitives.Semaphore`:
        >>> sem = primitives.ThreadsafeSemaphore(3)
        >>> my_coroutine = apply_semaphore(my_coroutine, sem)

    See Also:
        - :class:`asyncio.Semaphore`
        - :class:`primitives.Semaphore`

    Note:
        `primitives.Semaphore` is a subclass of `asyncio.Semaphore`. Therefore, when the documentation refers to `asyncio.Semaphore`, it also includes `primitives.Semaphore` and any other subclasses.
    """


def apply_semaphore(
    coro_fn: Optional[Union[CoroFn[P, T], SemaphoreSpec]] = None,
    semaphore: SemaphoreSpec = None,
) -> AsyncDecoratorOrCoroFn[P, T]:
    """Apply a semaphore to a coroutine function or return a decorator.

    This function can be used to apply a semaphore to a coroutine function either by
    passing the coroutine function and semaphore as arguments or by using the semaphore
    as a decorator. It raises exceptions if the inputs are not valid.

    Args:
        coro_fn (Optional[Callable]): The coroutine function to which the semaphore will be applied,
            or None if the semaphore is to be used as a decorator.
        semaphore (Union[int, asyncio.Semaphore, primitives.Semaphore]):
            The semaphore to apply, which can be an integer, an `asyncio.Semaphore`, or a `primitives.Semaphore`.

    Raises:
        ValueError: If `coro_fn` is an integer or `asyncio.Semaphore` and `semaphore` is not None.
        exceptions.FunctionNotAsync: If the provided function is not a coroutine.
        TypeError: If the semaphore is not an integer, an `asyncio.Semaphore`, or a `primitives.Semaphore`.

    Examples:
        Using as a decorator:
        >>> @apply_semaphore(2)
        ... async def limited_concurrent_function():
        ...     pass

        Applying directly to a function:
        >>> async def my_coroutine():
        ...     pass
        >>> my_coroutine = apply_semaphore(my_coroutine, 3)

        Handling invalid inputs:
        >>> try:
        ...     apply_semaphore(3, 2)
        ... except ValueError as e:
        ...     print(e)

    See Also:
        - :class:`asyncio.Semaphore`
        - :class:`primitives.Semaphore`

    Note:
        `primitives.Semaphore` is a subclass of `asyncio.Semaphore`. Therefore, when the documentation refers to `asyncio.Semaphore`, it also includes `primitives.Semaphore` and any other subclasses.
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
