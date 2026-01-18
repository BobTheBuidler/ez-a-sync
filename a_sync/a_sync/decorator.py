# mypy: disable-error-code=valid-type
from concurrent.futures import Executor
from typing import Literal, Union, overload

from typing_extensions import Unpack

from a_sync._typing import (AnyFn, CoroFn, DefaultMode, ModifierKwargs,
                            _ModifierKwargsNoDefault, _ModifierKwargsNoDefaultExecutor,
                            _ModifierKwargsNoExecutor, P, SyncFn, T)
from a_sync.a_sync import config
from a_sync.a_sync.function import (ASyncDecorator, ASyncDecoratorAsyncDefault,
                                    ASyncDecoratorSyncDefault, ASyncFunction,
                                    ASyncFunctionAsyncDefault, ASyncFunctionSyncDefault)

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


@overload
def a_sync(
    default: Literal["async"],
    executor: Executor,
    **modifiers: Unpack[_ModifierKwargsNoDefaultExecutor],
) -> ASyncDecoratorAsyncDefault:
    """
    Creates an asynchronous default decorator to run a sync function in an executor.

    Args:
        default: Specifies the default execution mode as 'async'.
        executor: The executor that will be used to call the sync function.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Basic usage with an asynchronous default:

        >>> @a_sync(default='async', executor=ThreadPoolExecutor(4))
        ... def my_function():
        ...     return True
        >>> await my_function()
        True
        >>> my_function(sync=True)
        True

    See Also:
        :class:`ASyncDecoratorAsyncDefault`
    """


@overload
def a_sync(
    default: Literal["async"],
    **modifiers: Unpack[_ModifierKwargsNoDefault],
) -> ASyncDecoratorAsyncDefault:
    """
    Creates an asynchronous default decorator.

    Args:
        default: Specifies the default execution mode as 'async'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Basic usage with an asynchronous default:

        >>> @a_sync(default='async')
        ... async def my_function():
        ...     return True
        >>> await my_function()
        True
        >>> my_function(sync=True)
        True

    See Also:
        :class:`ASyncDecoratorAsyncDefault`
    """


@overload
def a_sync(
    default: Literal["sync"],
    executor: Executor,
    **modifiers: Unpack[_ModifierKwargsNoDefaultExecutor],
) -> ASyncDecoratorSyncDefault:
    """
    Creates a synchronous default decorator to run a sync function in an executor when called asynchronously.

    Args:
        default: Specifies the default execution mode as 'sync'.
        executor: The executor that will be used to call the sync function.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Usage with an executor without specifying a default mode:

        >>> @a_sync(default="sync", executor=ThreadPoolExecutor(4))
        ... def my_function():
        ...     return True
        >>> my_function()
        True
        >>> await my_function(sync=False)
        True

    See Also:
        :class:`ASyncDecoratorSyncDefault`
    """


@overload
def a_sync(
    default: Literal["sync"],
    **modifiers: Unpack[_ModifierKwargsNoDefault],
) -> ASyncDecoratorSyncDefault:
    """
    Creates a synchronous default decorator.

    Args:
        default: Specifies the default execution mode as 'sync'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Basic usage with a synchronous default:

        >>> @a_sync(default='sync')
        ... def my_function():
        ...     return True
        >>> my_function()
        True
        >>> await my_function(sync=False)
        True

    See Also:
        :class:`ASyncDecoratorSyncDefault`
    """


@overload
def a_sync(
    executor: Executor,
    **modifiers: Unpack[_ModifierKwargsNoExecutor],
) -> ASyncDecoratorSyncDefault:
    """
    Creates a synchronous default decorator to run a sync function in an executor when called asynchronously.

    Args:
        executor: The executor that will be used to call the sync function.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Usage with an executor without specifying a default mode:

        >>> @a_sync(executor=ThreadPoolExecutor(4))
        ... def my_function():
        ...     return True
        >>> my_function()
        True
        >>> await my_function(sync=False)
        True

    See Also:
        :class:`ASyncDecoratorSyncDefault`
    """


@overload
def a_sync(
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecorator:
    """
    Creates a decorator with no default execution mode specified.

    Args:
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Usage without specifying a default mode:

        >>> @a_sync
        ... async def my_function():
        ...     return True
        >>> await my_function()
        True
        >>> my_function(sync=True)
        True

    See Also:
        :class:`ASyncDecorator`
    """


@overload  # async def, None default
def a_sync(
    coro_fn: CoroFn[P, T],
    default: Literal[None] = None,
    **modifiers: Unpack[_ModifierKwargsNoDefault],
) -> "ASyncFunctionAsyncDefault[P, T]":
    """
    Decorates an asynchronous function with no default execution mode specified.

    Args:
        coro_fn: The coroutine function to be decorated.
        default: Specifies no default execution mode.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Decorating an asynchronous function without a default mode:

        >>> async def my_function():
        ...     return True
        >>> decorated_function = a_sync(my_function)
        >>> await decorated_function()
        True
        >>> decorated_function(sync=True)
        True

    See Also:
        :class:`ASyncFunctionAsyncDefault`
    """


@overload  # sync def none default
def a_sync(
    coro_fn: SyncFn[P, T],
    default: Literal[None] = None,
    **modifiers: Unpack[_ModifierKwargsNoDefault],
) -> "ASyncFunctionSyncDefault[P, T]":
    """
    Decorates a synchronous function with no default execution mode specified.

    Args:
        coro_fn: The synchronous function to be decorated.
        default: Specifies no default execution mode.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Decorating a synchronous function without a default mode:

        >>> def my_function():
        ...     return True
        >>> decorated_function = a_sync(my_function)
        >>> decorated_function()
        True
        >>> await decorated_function(sync=False)
        True

    See Also:
        :class:`ASyncFunctionSyncDefault`
    """


@overload
def a_sync(
    coro_fn: Literal[None],
    default: Literal["async"],
    **modifiers: Unpack[_ModifierKwargsNoDefault],
) -> ASyncDecoratorAsyncDefault:
    """
    Creates an asynchronous default decorator with no function specified.

    Args:
        coro_fn: Specifies no function.
        default: Specifies the default execution mode as 'async'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Creating an asynchronous default decorator without a function:

        >>> @a_sync(default='async')
        ... async def my_function():
        ...     return True
        >>> await my_function()
        True
        >>> my_function(sync=True)
        True

    See Also:
        :class:`ASyncDecoratorAsyncDefault`
    """


@overload  # if you try to use default as the only arg
def a_sync(
    coro_fn: Literal["async"],
    default: Literal[None],
    **modifiers: Unpack[_ModifierKwargsNoDefault],
) -> ASyncDecoratorAsyncDefault:
    """
    Creates an asynchronous default decorator with no default execution mode specified.

    Args:
        coro_fn: Specifies the default execution mode as 'async'.
        default: Specifies no default execution mode.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Using 'async' as the only argument:

        >>> @a_sync('async')
        ... async def my_function():
        ...     return True
        >>> await my_function()
        True
        >>> my_function(sync=True)
        True

    See Also:
        :class:`ASyncDecoratorAsyncDefault`
    """


@overload  # async def, async default
def a_sync(
    coro_fn: CoroFn[P, T],
    default: Literal["async"],
    **modifiers: Unpack[_ModifierKwargsNoDefault],
) -> "ASyncFunctionAsyncDefault[P, T]":
    """
    Decorates an asynchronous function with an asynchronous default execution mode.

    Args:
        coro_fn: The coroutine function to be decorated.
        default: Specifies the default execution mode as 'async'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Decorating an asynchronous function with an async default:

        >>> async def my_function():
        ...     return True
        >>> decorated_function = a_sync(my_function, default='async')
        >>> await decorated_function()
        True
        >>> decorated_function(sync=True)
        True

    See Also:
        :class:`ASyncFunctionAsyncDefault`
    """


@overload  # sync def async default
def a_sync(
    coro_fn: SyncFn[P, T],
    default: Literal["async"],
    **modifiers: Unpack[_ModifierKwargsNoDefault],
) -> "ASyncFunctionAsyncDefault[P, T]":
    """
    Decorates a synchronous function with an asynchronous default execution mode.

    Args:
        coro_fn: The synchronous function to be decorated.
        default: Specifies the default execution mode as 'async'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Decorating a synchronous function with an async default:

        >>> def my_function():
        ...     return True
        >>> decorated_function = a_sync(my_function, default='async')
        >>> await decorated_function()
        True
        >>> decorated_function(sync=True)
        True

    See Also:
        :class:`ASyncFunctionAsyncDefault`
    """


@overload  # async def, sync default
def a_sync(
    coro_fn: CoroFn[P, T],
    default: Literal["sync"],
    **modifiers: Unpack[_ModifierKwargsNoDefault],
) -> ASyncFunctionSyncDefault:
    """
    Decorates an asynchronous function with a synchronous default execution mode.

    Args:
        coro_fn: The coroutine function to be decorated.
        default: Specifies the default execution mode as 'sync'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Decorating an asynchronous function with a sync default:

        >>> async def my_function():
        ...     return True
        >>> decorated_function = a_sync(my_function, default='sync')
        >>> decorated_function()
        True
        >>> await decorated_function(sync=False)
        True

    See Also:
        :class:`ASyncFunctionSyncDefault`
    """


@overload  # sync def sync default
def a_sync(
    coro_fn: SyncFn[P, T],
    default: Literal["sync"],
    **modifiers: Unpa