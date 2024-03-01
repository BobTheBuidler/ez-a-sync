
import functools

from a_sync._typing import *
from a_sync.modified import ASyncFunction, ModifiedMixin, ModifierManager

class ASyncDescriptor(ModifiedMixin, Generic[T]):
    __slots__ = "field_name", "_fget"
    def __init__(
        self, 
        _fget: AnyUnboundMethod[P, T], 
        field_name: Optional[str] = None, 
        **modifiers: ModifierKwargs,
    ) -> None:
        if not callable(_fget):
            raise ValueError(f'Unable to decorate {_fget}')
        self.modifiers = ModifierManager(modifiers)
        if isinstance(_fget, ASyncFunction):
            self.modifiers.update(_fget.modifiers)
            self.__wrapped__ = _fget
        elif asyncio.iscoroutinefunction(_fget):
            self.__wrapped__: AsyncUnboundMethod[P, T] = self.modifiers.apply_async_modifiers(_fget)
        else:
            self.__wrapped__ = _fget
        self.field_name = field_name or _fget.__name__
        functools.update_wrapper(self, self.__wrapped__)
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} for {self.__wrapped__}>"
    def __set_name__(self, owner, name):
        self.field_name = name
