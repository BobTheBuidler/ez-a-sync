"""
This module defines custom exceptions for the a_sync library.
"""

import asyncio

from a_sync._typing import *
from a_sync.a_sync._flags import VIABLE_FLAGS

if TYPE_CHECKING:
    from a_sync import TaskMapping


class ASyncFlagException(ValueError):
    """
    Base exception class for flag-related errors in the a_sync library.
    """

    viable_flags = VIABLE_FLAGS
    """
    The set of viable flags.

    A-Sync uses 'flags' to indicate whether objects / fn calls will be sync or async.
    You can use any of the provided flags, whichever makes most sense for your use case.
    """

    def desc(self, target) -> str:
        """
        Returns a description of the target for the flag error message.

        Args:
            target: The target object or string to describe.

        Returns:
            A string description of the target.
        """
        if target == "kwargs":
            return "flags present in 'kwargs'"
        else:
            return f"flag attributes defined on {target}"


class NoFlagsFound(ASyncFlagException):
    """
    Raised when no viable flags are found in the target.
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
        super().__init__(err)


class TooManyFlags(ASyncFlagException):
    """
    Raised when multiple flags are found, but only one was expected.
    """

    def __init__(self, target, present_flags):
        """
        Initializes the TooManyFlags exception.

        Args:
            target: The target object where flags were found.
            present_flags: The flags that were found.
        """
        err = f"There are multiple a_sync {self.__get_desc(target)} and there should only be one.\n"
        err += f"Present flags: {present_flags}\n"
        err += "This is likely an issue with a custom subclass definition."
        super().__init__(err)


class InvalidFlag(ASyncFlagException):
    """
    Raised when an invalid flag is encountered.
    """

    def __init__(self, flag: Optional[str]):
        """
        Initializes the InvalidFlag exception.

        Args:
            flag: The invalid flag.
        """
        err = f"'flag' must be one of: {self.viable_flags}. You passed {flag}."
        err += "\nThis code should not be reached and likely indicates an issue with a custom subclass definition."
        super().__init__(err)


class InvalidFlagValue(ASyncFlagException):
    """
    Raised when a flag has an invalid value.
    """

    def __init__(self, flag: str, flag_value: Any):
        """
        Initializes the InvalidFlagValue exception.

        Args:
            flag: The flag with an invalid value.
            flag_value: The invalid value of the flag.
        """
        super().__init__(f"'{flag}' should be boolean. You passed {flag_value}.")


class FlagNotDefined(ASyncFlagException):
    """
    Raised when a flag is not defined on an object.
    """

    def __init__(self, obj: Type, flag: str):
        """
        Initializes the FlagNotDefined exception.

        Args:
            obj: The object where the flag is not defined.
            flag: The undefined flag.
        """
        super().__init__(f"{obj} flag {flag} is not defined.")


class ImproperFunctionType(ValueError):
    """
    Raised when a function that should be sync is async or vice-versa.
    """


class FunctionNotAsync(ImproperFunctionType):
    """
    Raised when a function expected to be async is not.
    """

    def __init__(self, fn):
        """
        Initializes the FunctionNotAsync exception.

        Args:
            fn: The function that is not async.
        """
        super().__init__(
            f"`coro_fn` must be a coroutine function defined with `async def`. You passed {fn}."
        )


class FunctionNotSync(ImproperFunctionType):
    """
    Raised when a function expected to be sync is not.
    """

    def __init__(self, fn):
        """
        Initializes the FunctionNotSync exception.

        Args:
            fn: The function that is not sync.
        """
        super().__init__(
            f"`func` must be a coroutine function defined with `def`. You passed {fn}."
        )


class ASyncRuntimeError(RuntimeError):
    """
    Raised for runtime errors in asynchronous operations.
    """

    def __init__(self, e: RuntimeError):
        """
        Initializes the ASyncRuntimeError exception.

        Args:
            e: The original runtime error.
        """
        super().__init__(str(e))


class SyncModeInAsyncContextError(ASyncRuntimeError):
    """
    Raised when synchronous code is used within an asynchronous context.
    """

    def __init__(self, err: str = ""):
        """
        Initializes the SyncModeInAsyncContextError exception.
        """
        if not err:
            err = "The event loop is already running, which means you're trying to use an `ASyncFunction` synchronously from within an async context.\n"
            err += f"Check your traceback to determine which, then try calling asynchronously instead with one of the following kwargs:\n"
            err += f"{VIABLE_FLAGS}"
        super().__init__(err)


class MappingError(Exception):
    """
    Base class for errors related to :class:`~TaskMapping`.
    """

    _msg: str

    def __init__(self, mapping: "TaskMapping", msg: str = ""):
        """
        Initializes the MappingError exception.

        Args:
            mapping: The TaskMapping where the error occurred.
            msg: An optional message describing the error.
        """
        msg = msg or self._msg + f":\n{mapping}"
        if mapping:
            msg += f"\n{dict(mapping)}"
        super().__init__(msg)
        self.mapping = mapping


class MappingIsEmptyError(MappingError):
    """
    Raised when a TaskMapping is empty and an operation requires it to have items.
    """

    _msg = "TaskMapping does not contain anything to yield"


class MappingNotEmptyError(MappingError):
    """
    Raised when a TaskMapping is not empty and an operation requires it to be empty.
    """

    _msg = "TaskMapping already contains some data. In order to use `map`, you need a fresh one"


class PersistedTaskException(Exception):
    """
    Raised when an exception persists in an asyncio Task.
    """

    def __init__(self, exc: E, task: asyncio.Task) -> None:
        """
        Initializes the PersistedTaskException exception.

        Args:
            exc: The exception that persisted.
            task: The asyncio Task where the exception occurred.
        """
        super().__init__(f"{exc.__class__.__name__}: {exc}", task)
        self.exception = exc
        self.task = task


class EmptySequenceError(ValueError):
    """
    Raised when an operation is attempted on an empty sequence but items are required.
    """
