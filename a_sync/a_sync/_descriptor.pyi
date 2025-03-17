from a_sync._typing import *
from _typeshed import Incomplete
from a_sync import TaskMapping as TaskMapping
from a_sync.a_sync import decorator as decorator
from a_sync.a_sync.function import (
    ASyncFunction as ASyncFunction,
    ModifierManager as ModifierManager,
    _ModifiedMixin,
)
from a_sync.functools import (
    cached_property_unsafe as cached_property_unsafe,
    update_wrapper as update_wrapper,
)

class ASyncDescriptor(_ModifiedMixin, Generic[I, P, T]):
    __wrapped__: AnyFn[Concatenate[I, P], T]
    modifiers: Incomplete
    field_name: Incomplete
    def __init__(
        self,
        _fget: AnyFn[Concatenate[I, P], T],
        field_name: Optional[str] = None,
        **modifiers: ModifierKwargs
    ) -> None: ...
    def __set_name__(self, owner, name) -> None: ...
    def map(
        self, *instances: AnyIterable[I], **bound_method_kwargs: P.kwargs
    ) -> TaskMapping[I, T]: ...
    def all(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], bool]: ...
    def any(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], bool]: ...
    def min(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], T]: ...
    def max(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], T]: ...
    def sum(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], T]: ...
    def __init_subclass__(cls) -> None: ...
