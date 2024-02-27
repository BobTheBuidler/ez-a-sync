
import abc
import functools

from a_sync._typing import *
from a_sync.modified import ModifiedMixin, ModifierManager

class ASyncDescriptor(ModifiedMixin, Generic[T]):
    def __init__(self, _fget: UnboundMethod[ASyncInstance, P, T], field_name=None, **modifiers: ModifierKwargs):
        if not callable(_fget):
            raise ValueError(f'Unable to decorate {_fget}')
        self.modifiers = ModifierManager(modifiers)
        self._fn: UnboundMethod[ASyncInstance, P, T] = _fget
        self._fget: AsyncUnboundMethod[ASyncInstance, P, T] = self.modifiers.apply_async_modifiers(_fget) if asyncio.iscoroutinefunction(_fget) else self._asyncify(_fget)
        self.field_name = field_name or _fget.__name__
        functools.update_wrapper(self, _fget)
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} for {self._fn}>"
    def __set__(self, instance, value):
        raise RuntimeError(f"cannot set {self.field_name}")
    def __delete__(self, instance):
        raise RuntimeError(f"cannot delete {self.field_name}")
    def __set_name__(self, owner, name):
        self.field_name = name
