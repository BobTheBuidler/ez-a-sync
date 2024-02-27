
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
    def __set_name__(self, owner, name):
        self.field_name = name

def clean_default_from_modifiers(
    coro_fn: CoroFn[P, T],  # type: ignore [misc]
    modifiers: ModifierKwargs,
):
    from a_sync.modified import ASyncFunction
    # NOTE: We set the default here manually because the default set by the user will be used later in the code to determine whether to await.
    force_await = False
    if not asyncio.iscoroutinefunction(coro_fn) and not isinstance(coro_fn, ASyncFunction):
        if 'default' not in modifiers or modifiers['default'] != 'async':
            if 'default' in modifiers and modifiers['default'] == 'sync':
                force_await = True
            modifiers['default'] = 'async'
    return modifiers, force_await
