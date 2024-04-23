
import functools

from a_sync import decorator
from a_sync._typing import *
from a_sync.modified import ASyncFunction, ModifiedMixin, ModifierManager

if TYPE_CHECKING:
    from a_sync import TaskMapping

class ASyncDescriptor(ModifiedMixin, Generic[I, P, T]):
    __slots__ = "field_name", "_fget"
    def __init__(
        self, 
        _fget: AnyFn[Concatenate[I, P], T], 
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
            self.__wrapped__: AsyncUnboundMethod[I, P, T] = self.modifiers.apply_async_modifiers(_fget)
        else:
            self.__wrapped__ = _fget
        self.field_name = field_name or _fget.__name__
        functools.update_wrapper(self, self.__wrapped__)
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} for {self.__wrapped__}>"
    def __set_name__(self, owner, name):
        self.field_name = name
    def map(self, *instances: AnyIterable[I], **bound_method_kwargs: P.kwargs) -> "TaskMapping[I, T]":
        from a_sync.task import TaskMapping
        return TaskMapping(self, *instances, **bound_method_kwargs)
    @functools.cached_property
    def all(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], bool]:
        return decorator.a_sync(default=self.default)(self._all)
    @functools.cached_property
    def any(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], bool]:
        return decorator.a_sync(default=self.default)(self._any)
    @functools.cached_property
    def min(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], T]:
        return decorator.a_sync(default=self.default)(self._min)
    @functools.cached_property
    def max(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], T]:
        return decorator.a_sync(default=self.default)(self._max)
    @functools.cached_property
    def sum(self) -> ASyncFunction[Concatenate[AnyIterable[I], P], T]:
        return decorator.a_sync(default=self.default)(self._sum)
    async def _all(self, *instances: AnyIterable[I], concurrency: Optional[int] = None, name: str = "", **kwargs: P.kwargs) -> bool:
        return await self.map(*instances, concurrency=concurrency, name=name, **kwargs).all(pop=True, sync=False)
    async def _any(self, *instances: AnyIterable[I], concurrency: Optional[int] = None, name: str = "", **kwargs: P.kwargs) -> bool:
        return await self.map(*instances, concurrency=concurrency, name=name, **kwargs).any(pop=True, sync=False)
    async def _min(self, *instances: AnyIterable[I], concurrency: Optional[int] = None, name: str = "", **kwargs: P.kwargs) -> T:
        return await self.map(*instances, concurrency=concurrency, name=name, **kwargs).min(pop=True, sync=False)
    async def _max(self, *instances: AnyIterable[I], concurrency: Optional[int] = None, name: str = "", **kwargs: P.kwargs) -> T:
        return await self.map(*instances, concurrency=concurrency, name=name, **kwargs).max(pop=True, sync=False)
    async def _sum(self, *instances: AnyIterable[I], concurrency: Optional[int] = None, name: str = "", **kwargs: P.kwargs) -> T:
        return await self.map(*instances, concurrency=concurrency, name=name, **kwargs).sum(pop=True, sync=False)
