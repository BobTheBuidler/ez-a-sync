
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from concurrent.futures._base import Executor

EXECUTOR_TYPE = os.environ.get("A_SYNC_EXECUTOR_TYPE", "threads")
EXECUTOR_VALUE = int(os.environ.get("A_SYNC_EXECUTOR_VALUE", 8))

default_sync_executor: Executor
if EXECUTOR_TYPE.lower().startswith('p'): # p, P, proc, Processes, etc
    default_sync_executor = ProcessPoolExecutor(EXECUTOR_VALUE)
elif EXECUTOR_TYPE.lower().startswith('t'): # t, T, thread, THREADS, etc
    default_sync_executor = ThreadPoolExecutor(EXECUTOR_VALUE)
else:
    raise ValueError("Invalid value for A_SYNC_EXECUTOR_TYPE. Please use 'threads' or 'processes'.")
