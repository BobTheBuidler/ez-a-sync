"""
This module defines custom exceptions for the a_sync library.
"""

from asyncio import Task

from a_sync._typing import *
from a_sync.a_sync.flags import VIABLE_FLAGS

if TYPE_CHECKING:
    from a_sync import TaskMapping


class ASyncFlagException(ValueError):
    """
    Base exception class for flag-related errors in the a_sync library.

    A-Sync uses 'flags' to indicate whether objects or function calls will be sync or async.
    You can use any of the provided flags, which include 'sync' and 'asynchronous', whichever makes most sense for your use case.

    Examples:
        >>> try:
        ...     raise ASyncFlagException("An error occurred with flags.")
        ... except ASyncFlagException as e:
        ...     print(e)
        An error occurred with flags.

    See Also:
        - :const:`VIABLE_FLAGS`
    """

    viable_flags = VIABLE_FLAGS
    """The set of viable flags: {'sync', 'asynchronous'}."""

    def desc(self, target) -> str:
        """
        Returns a description of the target for the flag error message.

        Args:
            target: The target object or string to describe.

        Examples:
            >>> exception = ASyncFlagException()
            >>> exception.desc("kwargs")
            "flags present in 'kwargs'"

            >>> exception.desc("some_target")
            'flag attributes defined on some_target'
        """
        if target == "kwargs":
            return "flags present in 'kwargs'"
        else:
            return f"flag attributes defined on {target}"


class NoFlagsFound(ASyncFlagException):
    """
    Raised when no viable flags are found in the target.

    Examples:
        >>> try:
        ...     raise NoFlagsFound("some_target")
        ... except NoFlagsFound as e:
        ...     print(e)
        There are no viable a_sync flag attributes defined on some_target:
        Viable flags: {'sync', 'asynchronous'}
        This is likely an issue with a custom subclass definition.
    """

    def __init__(self, target, kwargs_keys=None):
        """
        Initializes the NoFlagsFound exception.

        Args:
            target: The target object where flags were expected.
            kwargs_keys: Optional; keys in the kwargs if applicable.
        """
        err = f"There are no viable a_sync {self.desc(target)}:"
        err += f"\nViable flags: {self.viable_flags}"
        if kwargs_keys:
            err += f"\nkwargs keys: {kwargs_keys}"
        err += "\nThis is likely an issue with a custom subclass definition."
        BaseException.__init__(self, err)


class TooManyFlags(ASyncFlagException):
    """
    Raised when multiple flags are found, but only one was expected.

    Examples:
        >>> try:
        ...     raise TooManyFlags("some_target", ["flag1", "flag2"])
        ... except TooManyFlags as e:
        ...     print(e)
        There are multiple a_sync flag attributes defined on some_target and there should only be one.
        Present flags: ['flag1', 'flag2']
        This is likely an issue with a custom subclass definition.
    """

    def __init__(self, target, present_flags):
        """
        Initializes the TooManyFlags exception.

        Args:
            target: The target object where flags were found.
            present_flags: The flags that were found.

        See Also:
            - :class:`ASyncFlagException`
        """
        err = f"There are multiple a_sync {self.desc(target)} and there should only be one.\n"
        err += f"Present flags: {present_flags}\n"
        err += "This is likely an issue with a custom subclass definition."
        BaseException.__init__(self, err)


class InvalidFlag(ASyncFlagException):
    """
    Raised when an invalid flag is encountered.

    Examples:
        >>> try:
        ...     raise InvalidFlag("invalid_flag")
        ... except InvalidFlag as e:
        ...     print(e)
        'flag' must be one of: {'sync', 'asynchronous'}. You passed invalid_flag.
        This code should not be reached and likely indicates an issue with a custom subclass definition.

    See Also:
        - :const:`VIABLE_FLAGS`
    """

    def __init__(self, flag: Optional[str]):
        """
        Initializes the InvalidFlag exception.

        Args:
            flag: The invalid flag.

        See Also:
            - :class:`ASyncFlagException`
        """
        err = f"'flag' must be one of: {self.viable_flags}. You passed {flag}."
        err += "\nThis code should not be reached and likely indicates an issue with a custom subclass definition."
        BaseException.__init__(self, err)


class InvalidFlagValue(ASyncFlagException):
    """
    Raised when a flag has an invalid value.

    Examples:
        >>> try:
        ...     raise InvalidFlagValue("some_flag", "not_a_boolean")
        ... except InvalidFlagValue as e:
        ...     print(e)
        'some_flag' should be boolean. You passed not_a_boolean.
    """

    def __init__(self, flag: str, flag_value: Any):
        """
        Initializes the InvalidFlagValue exception.

        Args:
            flag: The flag with an invalid value.
            flag_value: The invalid value of the flag.

        See Also:
            - :class:`ASyncFlagException`
        """
        BaseException.__init__(self, f"'{flag}' should be boolean. You passed {flag_value}.")


class FlagNotDefined(ASyncFlagException):
    """
    Raised when a flag is not defined on an object.

    Examples:
        >>> class SomeClass:
        ...     pass
        ...
        >>> try:
        ...     raise FlagNotDefined(SomeClass, "some_flag")
        ... except FlagNotDefined as e:
        ...     print(e)
        <class '__main__.SomeClass'> flag some_flag is not defined.
    """

    def __init__(self, obj: Type, flag: str):
        """
        Initializes the FlagNotDefined exception.

        Args:
            obj: The object where the flag is not defined.
            flag: The undefined flag.

        See Also:
            - :class:`ASyncFlagException`
        """
        BaseException.__init__(self, f"{obj} flag {flag} is not defined.")


class ImproperFunctionType(ValueError):
    """
    Raised when a function that should be sync is async or vice-versa.

    See Also:
        - :class:`FunctionNotAsync`
        - :class:`FunctionNotSync`
    """


class FunctionNotAsync(ImproperFunctionType):
    """
    Raised when a function expected to be async is not.

    Examples:
        >>> def some_function():
        ...     pass
        ...
        >>> try:
        ...     raise FunctionNotAsync(some_function)
        ... except FunctionNotAsync as e:
        ...     print(e)
        `coro_fn` must be a coroutine function defined with `async def`. You passed <function some_function at 0x...>.
    """

    def __init__(self, fn):
        """
        Initializes the FunctionNotAsync exception.

        Args:
            fn: The function that is not async.

        See Also:
            - :class:`ImproperFunctionType`
        """
        BaseException.__init__(
            self,
            f"`coro_fn` must be a coroutine function defined with `async def`. You passed {fn}.",
        )


class FunctionNotSync(ImproperFunctionType):
    """
    Raised when a function expected to be sync is actually async.

    Examples:
        >>> async def some_async_function():
        ...     pass
        ...
        >>> try:
        ...     raise FunctionNotSync(some_async_function)
        ... except FunctionNotSync as e:
        ...     print(e)
        `func` must be a coroutine function defined with `def`. You passed <function some_async_function at 0x...>.
    """

    def __init__(self, fn):
        """
        Initializes the FunctionNotSync exception.

        Args:
            fn: The function that is not sync.

        See Also:
            - :class:`ImproperFunctionType`
        """
        BaseException.__init__(
            self, f"`func` must be a coroutine function defined with `def`. You passed {fn}."
        )


class ASyncRuntimeError(RuntimeError):
    """
    Raised for runtime errors in asynchronous operations.

    Examples:
        >>> try:
        ...     raise ASyncRuntimeError(RuntimeError("Some runtime error"))
        ... except ASyncRuntimeError as e:
        ...     print(e)
        Some runtime error
    """

    def __init__(self, e: RuntimeError):
        """
        Initializes the ASyncRuntimeError exception.

        Args:
            e: The original runtime error.

        See Also:
            - :class:`RuntimeError`
        """
        BaseException.__init__(self, str(e))


class SyncModeInAsyncContextError(ASyncRuntimeError):
    """
    Raised when synchronous code is used within an asynchronous context.

    Examples:
        >>> try:
        ...     raise SyncModeInAsyncContextError()
        ... except SyncModeInAsyncContextError as e:
        ...     print(e)
        The event loop is already running, which means you're trying to use an `ASyncFunction` synchronously from within an async context.
        Check your traceback to determine which, then try calling asynchronously instead with one of the following kwargs:
        {'sync', 'asynchronous'}
    """

    def __init__(self, err: str = ""):
        """
        Initializes the SyncModeInAsyncContextError exception.

        See Also:
            - :class:`ASyncRuntimeError`
        """
        if not err:
            err = "The event loop is already running, which means you're trying to use an `ASyncFunction` synchronously from within an async context.\n"
            err += f"Check your traceback to determine which, then try calling asynchronously instead with one of the following kwargs:\n"
            err += f"{VIABLE_FLAGS}"
        BaseException.__init__(self, err)


class MappingError(Exception):
    """
    Base class for errors related to :class:`~TaskMapping`.

    Examples:
        >>> from a_sync import TaskMapping
        >>> try:
        ...     raise MappingError(TaskMapping(), "Some mapping error")
        ... except MappingError as e:
        ...     print(e)
        Some mapping error:
        <TaskMapping object at 0x...>
        {}
    """

    _msg: str

    def __init__(self, mapping: "TaskMapping", msg: str = ""):
        """
        Initializes the MappingError exception.

        Args:
            mapping: The TaskMapping where the error occurred.
            msg: An optional message describing the error.

        See Also:
            - :class:`TaskMapping`
        """
        msg = (msg or self._msg) + f":\n{mapping}"
        if mapping:
            msg += f"\n{dict(mapping)}"
        BaseException.__init__(self, msg)
        self.mapping = mapping


class MappingIsEmptyError(MappingError):
    """
    Raised when a TaskMapping is empty and an operation requires it to have items.

    Examples:
        >>> from a_sync import TaskMapping
        >>> try:
        ...     raise MappingIsEmptyError(TaskMapping())
        ... except MappingIsEmptyError as e:
        ...     print(e)
        TaskMapping does not contain anything to yield:
        <TaskMapping object at 0x...>
        {}
    """

    _msg = "TaskMapping does not contain anything to yield"


class MappingNotEmptyError(MappingError):
    """
    Raised when a TaskMapping is not empty and an operation requires it to be empty.

    Examples:
        >>> from a_sync import TaskMapping
        >>> task_mapping = TaskMapping()
        >>> task_mapping['key'] = 'value'
        >>> try:
        ...     raise MappingNotEmptyError(task_mapping)
        ... except MappingNotEmptyError as e:
        ...     print(e)
        TaskMapping already contains some data. In order to use `map`, you need a fresh one:
        <TaskMapping object at 0x...>
        {'key': 'value'}
    """

    _msg = "TaskMapping already contains some data. In order to use `map`, you need a fresh one"


class PersistedTaskException(Exception):
    """
    Raised when an exception persists in an asyncio Task.

    Examples:
        >>> import asyncio
        >>> async def some_task():
        ...     raise ValueError("Some error")
        ...
        >>> task = asyncio.create_task(some_task())
        >>> try:
        ...     raise PersistedTaskException(ValueError("Some error"), task)
        ... except PersistedTaskException as e:
        ...     print(e)
        ValueError: Some error
    """

    def __init__(self, exc: E, task: Task) -> None:
        """
        Initializes the PersistedTaskException exception.

        Args:
            exc: The exception that persisted.
            task: The asyncio Task where the exception occurred.

        See Also:
            - :class:`asyncio.Task`
        """
        BaseException.__init__(self, f"{exc.__class__.__name__}: {exc}", task)
        self.exception = exc
        self.task = task


class EmptySequenceError(ValueError):
    """
    Raised when an operation is attempted on an empty sequence but items are required.

    Examples:
        >>> try:
        ...     raise EmptySequenceError("Sequence is empty")
        ... except EmptySequenceError as e:
        ...     print(e)
        Sequence is empty
    """
