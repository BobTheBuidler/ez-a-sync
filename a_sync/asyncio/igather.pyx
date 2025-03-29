from asyncio import CancelledError, Future, current_task, ensure_future
from asyncio.futures import _get_loop
from asyncio.tasks import _GatheringFuture
from typing import Awaitable, Iterable, List, TypeVar

from a_sync._smart import smart_task_factory
from a_sync.a_sync._helpers import get_event_loop

T = TypeVar("T")


def igather(
    coros_or_futures: Iterable[Awaitable[T]], bint return_exceptions = False
) -> Awaitable[List[T]]:
    """A clone of asyncio.gather that takes a single iterator of coroutines instead of an unpacked tuple."""
    return cigather(coros_or_futures, return_exceptions=return_exceptions)


cdef object cigather(object coros_or_futures, bint return_exceptions = False):
    """A clone of asyncio.gather that takes a single iterator of coroutines instead of an unpacked tuple."""
    # NOTE: closures inside cpdef functions not yet supported, so we have this cdef helper
    cdef long long nfuts, nfinished
    cdef dict arg_to_fut = {}
    cdef list children = []
    loop = None
    for arg in coros_or_futures:
        if arg not in arg_to_fut:
            fut = ensure_future(arg, loop=loop)
            if loop is None:
                loop = _get_loop(fut)
            if fut is not arg:
                # 'arg' was not a Future, therefore, 'fut' is a new
                # Future created specifically for 'arg'.  Since the caller
                # can't control it, disable the "destroy pending task"
                # warning.
                fut._log_destroy_pending = False

            arg_to_fut[arg] = fut

        else:
            # There's a duplicate Future object in coros_or_futures.
            fut = arg_to_fut[arg]

        children.append(fut)

    if not children:
        return _get_empty_result_set_fut(get_event_loop())

    nfuts = len(arg_to_fut)
    nfinished = 0
    outer = None  # bpo-46672

    if return_exceptions:

        def _done_callback(fut: Future) -> None:
            # for some reason this wouldn't work until I added `return_exceptions=return_exceptions` to the func def
            nonlocal nfinished
            nfinished += 1

            if outer is None or outer.done():
                if not fut.cancelled():
                    # Mark exception retrieved.
                    fut.exception()
                return

            if nfinished == nfuts:
                # All futures are done; create a list of results
                # and set it to the 'outer' future.

                if outer._cancel_requested:
                    # If gather is being cancelled we must propagate the
                    # cancellation regardless of *return_exceptions* argument.
                    # See issue 32684.
                    outer.set_exception(fut._make_cancelled_error())
                else:
                    outer.set_result(list(map(_get_result_or_exc, children)))
    
    else:

        def _done_callback(fut: Future) -> None:
            # for some reason this wouldn't work until I added `return_exceptions=return_exceptions` to the func def
            nonlocal nfinished
            nfinished += 1

            if outer is None or outer.done():
                if not fut.cancelled():
                    # Mark exception retrieved.
                    fut.exception()
                return

            if fut.cancelled():
                # Check if 'fut' is cancelled first, as
                # 'fut.exception()' will *raise* a CancelledError
                # instead of returning it.
                outer.set_exception(fut._make_cancelled_error())
                return
            else:
                exc = fut.exception()
                if exc is not None:
                    outer.set_exception(exc)
                    return

            if nfinished == nfuts:
                # All futures are done; create a list of results
                # and set it to the 'outer' future.

                if outer._cancel_requested:
                    # If gather is being cancelled we must propagate the
                    # cancellation regardless of *return_exceptions* argument.
                    # See issue 32684.
                    exc = fut._make_cancelled_error()
                    outer.set_exception(exc)
                else:
                    outer.set_result(list(map(_get_result_or_exc, children)))
    
    if loop._task_factory is smart_task_factory:
        current = current_task()
        for fut in arg_to_fut.values():
            fut.add_done_callback(_done_callback)
            waiters = getattr(fut, "_waiters", None)
            if waiters is not None:
                waiters.add(current)
    else:
        for fut in arg_to_fut.values():
            fut.add_done_callback(_done_callback)

    outer = _GatheringFuture(children, loop=loop)
    
    return outer


cdef dict[object, object] _no_results_futs = {}


cdef object _get_empty_result_set_fut(loop):
    fut = _no_results_futs.get(loop)
    if fut is None:
        fut = _no_results_futs[loop] = loop.create_future()
        fut.set_result([])
    return fut


cdef object _get_result_or_exc(fut: Future):
    if fut.cancelled():
        # Check if 'fut' is cancelled first, as 'fut.exception()'
        # will *raise* a CancelledError instead of returning it.
        # Also, since we're adding the exception return value
        # to 'results' instead of raising it, don't bother
        # setting __context__.  This also lets us preserve
        # calling '_make_cancelled_error()' at most once.
        return CancelledError("" if fut._cancel_message is None else fut._cancel_message)
    res = fut.exception()
    if res is None:
        return fut.result()
    return res
