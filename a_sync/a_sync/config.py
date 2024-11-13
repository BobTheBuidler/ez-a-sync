"""
Configuration module for the a_sync library.

This module provides configuration options and default settings for the a_sync library.
It includes functionality for setting up executors, defining default modifiers,
and handling environment variable configurations.

Environment Variables:
    A_SYNC_EXECUTOR_TYPE: Specifies the type of executor to use. Valid values are
        strings that start with 'p' for ProcessPoolExecutor (e.g., 'processes')
        or 't' for ThreadPoolExecutor (e.g., 'threads'). Defaults to 'threads'.
    A_SYNC_EXECUTOR_VALUE: Specifies the number of workers for the executor.
        Defaults to 8.
    A_SYNC_DEFAULT_MODE: Sets the default mode for a_sync functions if not specified.
    A_SYNC_CACHE_TYPE: Sets the default cache type. If not specified, defaults to None.
    A_SYNC_CACHE_TYPED: Boolean flag to determine if cache keys should consider types.
    A_SYNC_RAM_CACHE_MAXSIZE: Sets the maximum size for the RAM cache. Defaults to -1.
    A_SYNC_RAM_CACHE_TTL: Sets the time-to-live for cache entries. Defaults to None.
    A_SYNC_RUNS_PER_MINUTE: Sets the rate limit for function execution.
    A_SYNC_SEMAPHORE: Sets the semaphore limit for function execution.
"""

import functools
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures._base import Executor

from a_sync._typing import *

EXECUTOR_TYPE = os.environ.get("A_SYNC_EXECUTOR_TYPE", "threads")
EXECUTOR_VALUE = int(os.environ.get("A_SYNC_EXECUTOR_VALUE", 8))


@functools.lru_cache(maxsize=1)
def get_default_executor() -> Executor:
    """Get the default executor based on the EXECUTOR_TYPE environment variable.

    Returns:
        An instance of either ProcessPoolExecutor or ThreadPoolExecutor.

    Raises:
        ValueError: If an invalid EXECUTOR_TYPE is specified. Valid values are
        strings that start with 'p' for ProcessPoolExecutor or 't' for ThreadPoolExecutor.
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
CACHE_TYPE: CacheType = (
    typ
    if (typ := os.environ.get("A_SYNC_CACHE_TYPE", "").lower())
    else null_modifiers["cache_type"]
)
CACHE_TYPED = bool(os.environ.get("A_SYNC_CACHE_TYPED"))
RAM_CACHE_MAXSIZE = int(os.environ.get("A_SYNC_RAM_CACHE_MAXSIZE", -1))
RAM_CACHE_TTL = (
    ttl
    if (ttl := float(os.environ.get("A_SYNC_RAM_CACHE_TTL", 0)))
    else null_modifiers["ram_cache_ttl"]
)

RUNS_PER_MINUTE = (
    rpm
    if (rpm := int(os.environ.get("A_SYNC_RUNS_PER_MINUTE", 0)))
    else null_modifiers["runs_per_minute"]
)
SEMAPHORE = (
    rpm
    if (rpm := int(os.environ.get("A_SYNC_SEMAPHORE", 0)))
    else null_modifiers["semaphore"]
)

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
