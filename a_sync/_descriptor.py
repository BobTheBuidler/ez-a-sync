
import functools

from a_sync._typing import *
from a_sync.modified import ASyncFunction, ModifiedMixin, ModifierManager

class ASyncDescriptor(ModifiedMixin, Generic[T]):
    __slots__ = "field_name", "_fget"
    def __init__(self, _fget: UnboundMethod[ASyncInstance, P, T], field_name=None, **modifiers: ModifierKwargs):
        if not callable(_fget):
            raise ValueError(f'Unable to decorate {_fget}')
        self.modifiers = ModifierManager(modifiers)
        if isinstance(_fget, ASyncFunction):
            self._fget = _fget
        elif asyncio.iscoroutinefunction(_fget):
            self._fget: AsyncUnboundMethod[ASyncInstance, P, T] = self.modifiers.apply_async_modifiers(_fget)
        else:
            self._fget = self._asyncify(_fget)
        self.field_name = field_name or _fget.__name__
        functools.update_wrapper(self, _fget)
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} for {self._fn}>"
    def __set_name__(self, owner, name):
        self.field_name = name
