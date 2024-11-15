"""
This module provides configuration options and default settings for the a_sync library.
It includes functionality for setting up executors, defining default modifiers,
and handling environment variable configurations.

Environment Variables:
    :obj:`~A_SYNC_EXECUTOR_TYPE`: Specifies the type of executor to use. Valid values are
        strings that start with 'p' for :class:`~concurrent.futures.ProcessPoolExecutor` 
        (e.g., 'processes') or 't' for :class:`~concurrent.futures.ThreadPoolExecutor` 
        (e.g., 'threads'). Defaults to 'threads'.
    :obj:`~A_SYNC_EXECUTOR_VALUE`: Specifies the number of workers for the executor.
        Defaults to 8.
    :obj:`~A_SYNC_DEFAULT_MODE`: Sets the default mode for a_sync functions if not specified.
    :obj:`~A_SYNC_CACHE_TYPE`: Sets the default cache type. If not specified, defaults to None.
    :obj:`~A_SYNC_CACHE_TYPED`: Boolean flag to determine if cache keys should consider types.
    :obj:`~A_SYNC_RAM_CACHE_MAXSIZE`: Sets the maximum size for the RAM cache. Defaults to -1.
    :obj:`~A_SYNC_RAM_CACHE_TTL`: Sets the time-to-live for cache entries. If not specified,
        defaults to 0, which is then checked against `null_modifiers["ram_cache_ttl"]` 
        to potentially set it to `None`, meaning cache entries do not expire by default.
    :obj:`~A_SYNC_RUNS_PER_MINUTE`: Sets the rate limit for function execution.
    :obj:`~A_SYNC_SEMAPHORE`: Sets the semaphore limit for function execution.

Examples:
    To set the executor type to use threads with 4 workers, set the environment variables:
    
    .. code-block:: bash

        export A_SYNC_EXECUTOR_TYPE=threads
        export A_SYNC_EXECUTOR_VALUE=4

    To configure caching with a maximum size of 100 and a TTL of 60 seconds:

    .. code-block:: bash

        export A_SYNC_CACHE_TYPE=memory
        export A_SYNC_RAM_CACHE_MAXSIZE=100
        export A_SYNC_RAM_CACHE_TTL=60

TODO: explain how and where these values are used

See Also:
    - :mod:`concurrent.futures`: For more details on executors.
    - :mod:`functools`: For caching mechanisms.
"""

import functools
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures._base import Executor

from a_sync._typing import *

EXECUTOR_TYPE = os.environ.get("A_SYNC_EXECUTOR_TYPE", "threads")
"""Specifies the type of executor to use.

Valid values are strings that start with 'p' for :class:`~concurrent.futures.ProcessPoolExecutor`
(e.g., 'processes') or 't' for :class:`~concurrent.futures.ThreadPoolExecutor` (e.g., 'threads').
Defaults to 'threads'.
"""

EXECUTOR_VALUE = int(os.environ.get("A_SYNC_EXECUTOR_VALUE", 8))
"""Specifies the number of workers for the executor. Defaults to 8."""


@functools.lru_cache(maxsize=1)
def get_default_executor() -> Executor:
    """Get the default executor based on the EXECUTOR_TYPE environment variable.

    Returns:
        An instance of either :class:`~concurrent.futures.ProcessPoolExecutor`
        or :class:`~concurrent.futures.ThreadPoolExecutor`.

    Raises:
        ValueError: If an invalid EXECUTOR_TYPE is specified. Valid values are
        strings that start with 'p' for :class:`~concurrent.futures.ProcessPoolExecutor`
        or 't' for :class:`~concurrent.futures.ThreadPoolExecutor`.

    Examples:
        >>> import os
        >>> os.environ["A_SYNC_EXECUTOR_TYPE"] = "threads"
        >>> executor = get_default_executor()
        >>> isinstance(executor, ThreadPoolExecutor)
        True

        >>> os.environ["A_SYNC_EXECUTOR_TYPE"] = "processes"
        >>> executor = get_default_executor()
        >>> isinstance(executor, ProcessPoolExecutor)
        True
    """
    if EXECUTOR_TYPE.lower().startswith("p"):  # p, P, proc, Processes, etc
        return ProcessPoolExecutor(EXECUTOR_VALUE)
    elif EXECUTOR_TYPE.lower().startswith("t"):  # t, T, thread, THREADS, etc
        return ThreadPoolExecutor(EXECUTOR_VALUE)
    raise ValueError(
        "Invalid value for A_SYNC_EXECUTOR_TYPE. Please use 'threads' or 'processes'."
    )


default_sync_executor = get_default_executor()

null_modifiers = ModifierKwargs(
    default=None,
    cache_type=None,
    cache_typed=False,
    ram_cache_maxsize=-1,
    ram_cache_ttl=None,
    runs_per_minute=None,
    semaphore=None,
    executor=default_sync_executor,
)

#####################
# Default Modifiers #
#####################

# User configurable default modifiers to be applied to any a_sync decorated function if you do not specify kwarg values for each modifier.

DEFAULT_MODE: DefaultMode = os.environ.get("A_SYNC_DEFAULT_MODE")  # type: ignore [assignment]
"""Sets the default mode for a_sync functions if not specified."""

CACHE_TYPE: CacheType = (
    typ
    if (typ := os.environ.get("A_SYNC_CACHE_TYPE", "").lower())
    else null_modifiers["cache_type"]
)
"""Sets the default cache type. If not specified, defaults to None."""

CACHE_TYPED = bool(os.environ.get("A_SYNC_CACHE_TYPED"))
"""Boolean flag to determine if cache keys should consider types."""

RAM_CACHE_MAXSIZE = int(os.environ.get("A_SYNC_RAM_CACHE_MAXSIZE", -1))
"""
Sets the maximum size for the RAM cache. Defaults to -1.
# TODO: explain what -1 does
"""

RAM_CACHE_TTL = (
    ttl
    if (ttl := float(os.environ.get("A_SYNC_RAM_CACHE_TTL", 0)))
    else null_modifiers["ram_cache_ttl"]
)
"""
Sets the time-to-live for cache entries. If not specified, defaults to 0, which is then checked against
`null_modifiers["ram_cache_ttl"]`  to potentially set it to `None`, meaning cache entries do not expire
by default.
"""


RUNS_PER_MINUTE = (
    rpm
    if (rpm := int(os.environ.get("A_SYNC_RUNS_PER_MINUTE", 0)))
    else null_modifiers["runs_per_minute"]
)
"""Sets the rate limit for function execution."""

SEMAPHORE = (
    rpm
    if (rpm := int(os.environ.get("A_SYNC_SEMAPHORE", 0)))
    else null_modifiers["semaphore"]
)
"""Sets the semaphore limit for function execution."""

user_set_default_modifiers = ModifierKwargs(
    default=DEFAULT_MODE,
    cache_type=CACHE_TYPE,
    cache_typed=CACHE_TYPED,
    ram_cache_maxsize=RAM_CACHE_MAXSIZE,
    ram_cache_ttl=RAM_CACHE_TTL,
    runs_per_minute=RUNS_PER_MINUTE,
    semaphore=SEMAPHORE,
    executor=default_sync_executor,
)
