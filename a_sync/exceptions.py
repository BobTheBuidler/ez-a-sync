
from typing import Any, Set


class ASyncFlagException(ValueError):
    @property
    def viable_flags(self) -> Set[str]:
        from a_sync._flags import VIABLE_FLAGS
        return VIABLE_FLAGS

    def desc(self, target) -> str:
        if target == 'kwargs':
            return "flags present in 'kwargs'"
        else:
            return f'flag attributes defined on {target}'

class NoFlagsFound(ASyncFlagException):
    def __init__(self, target, kwargs_keys=None):
        err = f"There are no viable a_sync {self.desc(target)}:"
        err += f"\nViable flags: {self.viable_flags}"
        if kwargs_keys:
            err += f"\nkwargs keys: {kwargs_keys}"
        err += "\nThis is likely an issue with a custom subclass definition."
        super().__init__(err)

class TooManyFlags(ASyncFlagException):
    def __init__(self, target, present_flags):
        err = f"There are multiple a_sync {self.__get_desc(target)} and there should only be one.\n"
        err += f"Present flags: {present_flags}\n"
        err += "This is likely an issue with a custom subclass definition."
        super().__init__(err)

class InvalidFlag(ASyncFlagException):
    def __init__(self, flag: str):
        err = f"'flag' must be one of: {self.viable_flags}. You passed {flag}."
        err += "\nThis code should not be reached and likely indicates an issue with a custom subclass definition."
        super().__init__(err)

class InvalidFlagValue(ASyncFlagException):
    def __init__(self, flag: str, flag_value: Any):
        super().__init__(f"'{flag}' should be boolean. You passed {flag_value}.")



class ImproperFunctionType(ValueError):
    pass

class FunctionNotAsync(ImproperFunctionType):
    def __init__(self, fn):
        super().__init__(f"'coro_fn' must be a coroutine function defined with 'async def'. You passed {fn}.")
