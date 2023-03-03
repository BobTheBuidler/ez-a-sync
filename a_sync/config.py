
import functools
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures._base import Executor

from a_sync._typing import *

EXECUTOR_TYPE = os.environ.get("A_SYNC_EXECUTOR_TYPE", "threads")
EXECUTOR_VALUE = int(os.environ.get("A_SYNC_EXECUTOR_VALUE", 8))

@functools.lru_cache(maxsize=1)
def get_default_executor() -> Executor:
    if EXECUTOR_TYPE.lower().startswith('p'): # p, P, proc, Processes, etc
        return ProcessPoolExecutor(EXECUTOR_VALUE)
    elif EXECUTOR_TYPE.lower().startswith('t'): # t, T, thread, THREADS, etc
        return ThreadPoolExecutor(EXECUTOR_VALUE)
    raise ValueError("Invalid value for A_SYNC_EXECUTOR_TYPE. Please use 'threads' or 'processes'.")

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
CACHE_TYPE: CacheType = typ if (typ := os.environ.get("A_SYNC_CACHE_TYPE", "").lower()) else null_modifiers['cache_type']
CACHE_TYPED = bool(os.environ.get("A_SYNC_CACHE_TYPED"))
RAM_CACHE_MAXSIZE = int(os.environ.get("A_SYNC_RAM_CACHE_MAXSIZE", -1)) 
RAM_CACHE_TTL = ttl if (ttl := float(os.environ.get("A_SYNC_RAM_CACHE_TTL", 0))) else null_modifiers['ram_cache_ttl']

RUNS_PER_MINUTE = rpm if (rpm := int(os.environ.get("A_SYNC_RUNS_PER_MINUTE", 0))) else null_modifiers['runs_per_minute']
SEMAPHORE = rpm if (rpm := int(os.environ.get("A_SYNC_SEMAPHORE", 0))) else null_modifiers['semaphore']

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
