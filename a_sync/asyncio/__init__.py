"""
This package provides custom utilities and extensions to the built-in `asyncio` package.

These utilities include enhanced versions of common asyncio functions, offering additional
features and improved functionality for asynchronous programming.

Modules:
- :func:`create_task`: Extends `asyncio.create_task` to support any `Awaitable`, manage task lifecycle, and enhance error handling.
- :func:`gather`: Provides an enhanced version of `asyncio.gather` with additional features like progress reporting and exclusion of results based on a condition.
- :func:`as_completed`: Extends `asyncio.as_completed` with additional functionality such as progress reporting using `tqdm`.
- :func:`get_event_loop`: Utility to get the current event loop, creating a new one if none exists.

See Also:
    - `asyncio <https://docs.python.org/3/library/asyncio.html>`_: The standard asyncio library documentation for more details on the original functions.
"""

from a_sync.a_sync._helpers import get_event_loop
from a_sync.asyncio.create_task import create_task
from a_sync.asyncio.as_completed import as_completed
from a_sync.asyncio.igather import igather
from a_sync.asyncio.gather import gather, cgather
from a_sync.asyncio.sleep import sleep0

__all__ = [
    "create_task",
    "gather",
    "cgather",
    "igather",
    "as_completed",
    "get_event_loop",
    "sleep0",
]


# Function: create_task
"""
Extends `asyncio.create_task` to support any `Awaitable`, manage task lifecycle, and enhance error handling.

This function accepts any `Awaitable`, ensuring broader compatibility. If the `Awaitable` is not a coroutine,
it attempts to convert it to one. It optionally prevents the task from being garbage-collected until completion
and provides enhanced error management by wrapping exceptions in a custom exception when `skip_gc_until_done` is True.

Args:
    coro: An `Awaitable` object from which to create the task. If not a coroutine, it will be converted.
    name: Optional name for the task, aiding in debugging.
    skip_gc_until_done: If True, the task is kept alive until it completes, preventing garbage collection.
                        Exceptions are wrapped in `PersistedTaskException` for special handling.
    log_destroy_pending: If False, asyncio's default error log when a pending task is destroyed is suppressed.

Examples:
    Basic usage:
    ```
    task = create_task(some_coroutine())
    ```

    With options:
    ```
    task = create_task(some_coroutine(), name="MyTask", skip_gc_until_done=True)
    ```

See Also:
    - :func:`asyncio.create_task`: The original asyncio function.
"""


# Function: gather
"""
Provides an enhanced version of :func:`asyncio.gather`.

This function extends Python's `asyncio.gather`, providing additional features for handling either individual awaitable objects or a mapping of awaitables.

Differences from `asyncio.gather`:
- Uses type hints for use with static type checkers.
- Supports gathering either individual awaitables or a k:v mapping of awaitables.
- Provides progress reporting using `tqdm` if 'tqdm' is set to True.
- Allows exclusion of results based on a condition using the 'exclude_if' parameter.

Args:
    *awaitables: The awaitables to await concurrently. It can be a list of individual awaitables or a mapping of awaitables.
    return_exceptions: If True, exceptions are returned as results instead of raising them. Defaults to False.
    exclude_if: A callable that takes a result and returns True if the result should be excluded from the final output. Defaults to None.
    tqdm: If True, enables progress reporting using `tqdm`. Defaults to False.
    **tqdm_kwargs: Additional keyword arguments for `tqdm` if progress reporting is enabled.

Examples:
    Awaiting individual awaitables:
    ```
    results = await gather(thing1(), thing2())
    ```

    Awaiting a mapping of awaitables:
    ```
    mapping = {'key1': thing1(), 'key2': thing2()}
    results = await gather(mapping)
    ```

See Also:
    - :func:`asyncio.gather`: The original asyncio function.
"""


# Function: as_completed
"""
Extends Python's :func:`asyncio.as_completed` with additional functionality.

This function extends Python's `asyncio.as_completed`, providing additional features for mixed use cases of individual awaitable objects and mappings of awaitables.

Differences from `asyncio.as_completed`:
- Uses type hints for use with static type checkers.
- Supports either individual awaitables or a k:v mapping of awaitables.
- Can be used as an async iterator which yields the result values.
- Provides progress reporting using `tqdm` if 'tqdm' is set to True.

Args:
    fs: The awaitables to await concurrently. It can be a list of individual awaitables or a mapping of awaitables.
    timeout: The maximum time, in seconds, to wait for the completion of awaitables. Defaults to None (no timeout).
    return_exceptions: If True, exceptions are returned as results instead of raising them. Defaults to False.
    aiter: If True, returns an async iterator of results. Defaults to False.
    tqdm: If True, enables progress reporting using `tqdm`. Defaults to False.
    **tqdm_kwargs: Additional keyword arguments for `tqdm` if progress reporting is enabled.

Examples:
    Awaiting individual awaitables:
    ```
    awaitables = [async_function1(), async_function2()]
    for coro in as_completed(awaitables):
        val = await coro
    ```

    Awaiting mappings of awaitables:
    ```
    mapping = {'key1': async_function1(), 'key2': async_function2()}
    for coro in as_completed(mapping):
        k, v = await coro
    ```

See Also:
    - :func:`asyncio.as_completed`: The original asyncio function.
"""


# Function: get_event_loop
"""
Utility to get the current event loop, creating a new one if none exists.

This function attempts to get the current event loop. If no event loop is found (which can occur in multi-threaded applications), it creates a new event loop and sets it as the current event loop.

Examples:
    Basic usage:
    ```
    loop = get_event_loop()
    ```

    Handling in multi-threaded applications:
    ```
    try:
        loop = get_event_loop()
    except RuntimeError:
        print("No current event loop found.")
    ```

See Also:
    - :func:`asyncio.get_event_loop`: The original asyncio function.
"""
