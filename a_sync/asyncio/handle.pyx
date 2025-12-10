import asyncio
from asyncio.events import AbstractEventLoop
from typiing import Any, Callable, List, Optional


Callback =  Callable[[asyncio.Task[Any]], None]

cdef class Handle:
    """Object returned by callback registration methods."""

    cdef bint _cancelled
    # TODO: cdef more attributes

    def __cinit__(self) -> None:
        self._cancelled = False
        
    def __init__(
        self,
        callback: Optional[Callback],
        args: Tuple[Any, ...],
        loop: AbstractEventLoop,
        context=None,
    ) -> None:
        if context is None:
            context = contextvars.copy_context()
        self._context = context
        self._loop = loop
        self._callback = callback
        self._args = args
        self._repr: Optional[str] = None
        if self._loop.get_debug():
            self._source_traceback = format_helpers.extract_stack(
                sys._getframe(1))
        else:
            self._source_traceback = None

    def _repr_info(self) -> List[str]:
        info = [self.__class__.__name__]
        if self._cancelled:
            info.append('cancelled')
        if self._callback is not None:
            info.append(format_helpers._format_callback_source(
                self._callback, self._args))
        if self._source_traceback:
            frame = self._source_traceback[-1]
            info.append(f'created at {frame[0]}:{frame[1]}')
        return info

    def __repr__(self) -> str:
        if self._repr is not None:
            return self._repr
        info = self._repr_info()
        return '<{}>'.format(' '.join(info))

    def cancel(self) -> None:
        if not self._cancelled:
            self._cancelled = True
            if self._loop.get_debug():
                # Keep a representation in debug mode to keep callback and
                # parameters. For example, to log the warning
                # "Executing <Handle...> took 2.5 second"
                self._repr = repr(self)
            self._callback = None
            self._args = None

    def cancelled(self) -> bool:
        return self._cancelled

    def _run(self) -> None:
        try:
            self._context.run(self._callback, *self._args)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as exc:
            cb = format_helpers._format_callback_source(
                self._callback, self._args)
            msg = f'Exception in callback {cb}'
            context = {
                'message': msg,
                'exception': exc,
                'handle': self,
            }
            if self._source_traceback:
                context['source_traceback'] = self._source_traceback
            self._loop.call_exception_handler(context)
        self = None  # Needed to break cycles when an exception occurs.


cdef class TimerHandle(Handle):
    """Object returned by timed callback registration methods."""

    cdef float _when
    cdef bint _scheduled

    def __cinit__(self) -> None:
        self._scheduled = False
        
    def __init__(
        self,
        when: float,
        callback: Callback,
        args: Tuple[Any, ...],
        loop: AbstractEventLoop,
        context=None,
    ):
        assert when is not None
        super().__init__(callback, args, loop, context)
        if self._source_traceback:
            del self._source_traceback[-1]
        self._when = when

    def _repr_info(self) -> List[str]:
        info = super()._repr_info()
        pos = 2 if self._cancelled else 1
        info.insert(pos, f'when={self._when}')
        return info

    def __hash__(self) -> int:
        return hash(self._when)

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, TimerHandle):
            return self._when < other._when
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if isinstance(other, TimerHandle):
            return self._when < other._when or self.__eq__(other)
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, TimerHandle):
            return self._when > other._when
        return NotImplemented

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, TimerHandle):
            return self._when > other._when or self.__eq__(other)
        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TimerHandle):
            return (self._when == other._when and
                    self._callback == other._callback and
                    self._args == other._args and
                    self._cancelled == other._cancelled)
        return NotImplemented

    def cancel(self) -> None:
        if not self._cancelled:
            self._loop._timer_handle_cancelled(self)
        super().cancel()

    def when(self) -> float:
        """Return a scheduled callback time.

        The time is an absolute timestamp, using the same time
        reference as loop.time().
        """
        return self._when
