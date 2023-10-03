# type: ignore [var-annotated]

import asyncio
from decimal import Decimal
from functools import partial, wraps
from typing import (Any, Awaitable, Callable, List, Set, TypeVar, Union,
                    overload)

from typing_extensions import ParamSpec, Unpack

from a_sync._typing import ModifierKwargs

T = TypeVar('T')
P = ParamSpec('P')
MaybeMeta = Union[T, "ASyncFuture[T]"]

def future(callable: Union[Callable[P, Awaitable[T]], Callable[P, T]] = None, **kwargs: Unpack[ModifierKwargs]) -> Callable[P, "ASyncFuture[T]"]:
    return _ASyncFutureWrappedFn(callable, **kwargs)

async def _gather_check_and_materialize(*things: Unpack[MaybeMeta[T]]) -> List[T]:
    return await asyncio.gather(*[_check_and_materialize(thing) for thing in things])

async def _check_and_materialize(thing: T) -> T:
    return await thing if isinstance(thing, ASyncFuture) else thing
    
def _materialize(meta: "ASyncFuture[T]") -> T:
    if meta.done():
        return asyncio.Future.result(meta) #.result()
    if meta._started:
        raise Exception("this shouldn't happen when running synchronously")
    try:
        meta._started = True
        retval = asyncio.get_event_loop().run_until_complete(meta._awaitable)
        meta.set_result(retval)
        meta._done.set()
        return retval
    except RuntimeError as e:
        raise RuntimeError(f"{meta} result is not set and the event loop is running, you will need to await it first") from e

Numeric = Union[int, float, Decimal, "ASyncFuture[int]", "ASyncFuture[float]", "ASyncFuture[Decimal]"]

class ASyncFuture(asyncio.Future, Awaitable[T]):
    def __init__(self, awaitable: Awaitable[T], dependencies: List["ASyncFuture"] = []) -> None:
        self._awaitable = awaitable
        self._dependencies = dependencies
        for dependency in dependencies:
            assert isinstance(dependency, ASyncFuture)
            dependency._dependants.append(self)
        self._dependants: List[ASyncFuture] = []
        self._started = False
        self._done = asyncio.Event()
        super().__init__()
    def __hash__(self) -> int:
        return hash(self._awaitable)
    @property
    def dependants(self) -> Set["ASyncFuture"]:
        dependants = set()
        for dep in self._dependants:
            dependants.add(dep)
            dependants.union(dep.dependants)
        return dependants
    @property
    def dependencies(self) -> Set["ASyncFuture"]:
        dependencies = set()
        for dep in self._dependencies:
            dependencies.add(dep)
            dependencies.union(dep.dependencies)
        return dependencies
    def __repr__(self) -> str:
        string = f"<{self.__class__.__name__} {self._state} for {self._awaitable}"
        if self.cancelled():
            pass
        elif self.done():
            string += f" exception={self.exception()}" if self.exception() else f" result={super().result()}"
        return string + ">"
    def __list_dependencies(self, other) -> List["ASyncFuture"]:
        if isinstance(other, ASyncFuture):
            return [self, other]
        return [self]
    @property
    def result(self) -> Union[Callable[[], T], Any]:
        if hasattr(r := super().result(), 'result'):
            # can be property, method, whatever. should work.
            return r.result
        # the result should be callable like an asyncio.Future
        return super().result
    def __getattr__(self, attr: str) -> Any:
        return getattr(_materialize(self), attr)
    def __getitem__(self, key) -> Any:
        return _materialize(self)[key]
    # NOTE: broken, do not use. I think
    def __setitem__(self, key, value) -> None:
        _materialize(self)[key] = value
    def __sizeof__(self) -> int:
        if isinstance(self._awaitable, Coroutine):
            return sum(sys.getsizeof(v) for v in self._awaitable.cr_frame.f_locals.values())
        elif isinstance(self._awaitable, asyncio.Future):
            raise NotImplementedError
        raise NotImplementedError
    # not sure what to call these
    def __contains__(self, key: Any) -> bool:
        return _materialize(ASyncFuture(self.__contains(key), dependencies=self.__list_dependencies(key)))
    def __await__(self) -> Awaitable[T]:
        return self.__await().__await__()
    async def __await(self) -> T:
        if self.done():
            return super().result()
        if self._started:
            await self._done.wait()
            return super().result()
        self._started = True
        self.set_result(await self._awaitable)
        self._done.set()
        return self._result
    def __iter__(self):
        return _materialize(self).__iter__()
    def __next__(self):
        return _materialize(self).__next__()
    def __enter__(self):
        return _materialize(self).__enter__()
    def __exit__(self, *args):
        return _materialize(self).__exit__(*args)
    @overload
    def __add__(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]":...
    @overload
    def __add__(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]":...
    @overload
    def __add__(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]":...
    @overload
    def __add__(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]":...
    @overload
    def __add__(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    def __add__(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]":...
    @overload
    def __add__(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    def __add__(self: "ASyncFuture[int]", other: "ASyncFuture[int]") -> "ASyncFuture[int]":...
    @overload
    def __add__(self: "ASyncFuture[float]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    def __add__(self: "ASyncFuture[float]", other: "ASyncFuture[int]") -> "ASyncFuture[float]":...
    @overload
    def __add__(self: "ASyncFuture[int]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    def __add__(self: "ASyncFuture[Decimal]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    @overload
    def __add__(self: "ASyncFuture[Decimal]", other: "ASyncFuture[int]") -> "ASyncFuture[Decimal]":...
    @overload
    def __add__(self: "ASyncFuture[int]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    def __add__(self, other: Numeric) -> "ASyncFuture":
        return ASyncFuture(self.__add(other), dependencies=self.__list_dependencies(other))
    @overload
    def __sub__(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]":...
    @overload
    def __sub__(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]":...
    @overload
    def __sub__(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]":...
    @overload
    def __sub__(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]":...
    @overload
    def __sub__(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    def __sub__(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]":...
    @overload
    def __sub__(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    def __sub__(self: "ASyncFuture[int]", other: "ASyncFuture[int]") -> "ASyncFuture[int]":...
    @overload
    def __sub__(self: "ASyncFuture[float]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    def __sub__(self: "ASyncFuture[float]", other: "ASyncFuture[int]") -> "ASyncFuture[float]":...
    @overload
    def __sub__(self: "ASyncFuture[int]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    def __sub__(self: "ASyncFuture[Decimal]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    @overload
    def __sub__(self: "ASyncFuture[Decimal]", other: "ASyncFuture[int]") -> "ASyncFuture[Decimal]":...
    @overload
    def __sub__(self: "ASyncFuture[int]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    def __sub__(self, other: Numeric) -> "ASyncFuture":
        return ASyncFuture(self.__sub(other), dependencies=self.__list_dependencies(other))
    def __mul__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__mul(other), dependencies=self.__list_dependencies(other))
    def __pow__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__pow(other), dependencies=self.__list_dependencies(other))
    def __truediv__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__truediv(other), dependencies=self.__list_dependencies(other))
    def __floordiv__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__floordiv(other), dependencies=self.__list_dependencies(other))
    def __pow__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__pow(other), dependencies=self.__list_dependencies(other))
    @overload
    def __radd__(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]":...
    @overload
    def __radd__(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]":...
    @overload
    def __radd__(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]":...
    @overload
    def __radd__(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]":...
    @overload
    def __radd__(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    def __radd__(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]":...
    @overload
    def __radd__(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    def __radd__(self: "ASyncFuture[int]", other: "ASyncFuture[int]") -> "ASyncFuture[int]":...
    @overload
    def __radd__(self: "ASyncFuture[float]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    def __radd__(self: "ASyncFuture[float]", other: "ASyncFuture[int]") -> "ASyncFuture[float]":...
    @overload
    def __radd__(self: "ASyncFuture[int]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    def __radd__(self: "ASyncFuture[Decimal]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    @overload
    def __radd__(self: "ASyncFuture[Decimal]", other: "ASyncFuture[int]") -> "ASyncFuture[Decimal]":...
    @overload
    def __radd__(self: "ASyncFuture[int]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    def __radd__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__radd(other), dependencies=self.__list_dependencies(other))
    
    @overload
    def __rsub__(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]":...
    @overload
    def __rsub__(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]":...
    @overload
    def __rsub__(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]":...
    @overload
    def __rsub__(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]":...
    @overload
    def __rsub__(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    def __rsub__(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]":...
    @overload
    def __rsub__(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    def __rsub__(self: "ASyncFuture[int]", other: "ASyncFuture[int]") -> "ASyncFuture[int]":...
    @overload
    def __rsub__(self: "ASyncFuture[float]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    def __rsub__(self: "ASyncFuture[float]", other: "ASyncFuture[int]") -> "ASyncFuture[float]":...
    @overload
    def __rsub__(self: "ASyncFuture[int]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    def __rsub__(self: "ASyncFuture[Decimal]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    @overload
    def __rsub__(self: "ASyncFuture[Decimal]", other: "ASyncFuture[int]") -> "ASyncFuture[Decimal]":...
    @overload
    def __rsub__(self: "ASyncFuture[int]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    def __rsub__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__rsub(other), dependencies=self.__list_dependencies(other))
    def __rmul__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__rmul(other), dependencies=self.__list_dependencies(other))
    def __rtruediv__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__rtruediv(other), dependencies=self.__list_dependencies(other))
    def __rfloordiv__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__rfloordiv(other), dependencies=self.__list_dependencies(other))
    def __rpow__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__rpow(other), dependencies=self.__list_dependencies(other))
    def __eq__(self, other) -> "ASyncFuture":
        return bool(ASyncFuture(self.__eq(other), dependencies=self.__list_dependencies(other)))
    def __gt__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__gt(other), dependencies=self.__list_dependencies(other))
    def __ge__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__ge(other), dependencies=self.__list_dependencies(other))
    def __lt__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__lt(other), dependencies=self.__list_dependencies(other))
    def __le__(self, other) -> "ASyncFuture":
        return ASyncFuture(self.__le(other), dependencies=self.__list_dependencies(other))
    
    # Maths
    
    @overload
    async def __add(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]":...
    @overload
    async def __add(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]":...
    @overload
    async def __add(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]":...
    @overload
    async def __add(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]":...
    @overload
    async def __add(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    async def __add(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]":...
    @overload
    async def __add(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    async def __add(self: "ASyncFuture[int]", other: "ASyncFuture[int]") -> "ASyncFuture[int]":...
    @overload
    async def __add(self: "ASyncFuture[float]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    async def __add(self: "ASyncFuture[float]", other: "ASyncFuture[int]") -> "ASyncFuture[float]":...
    @overload
    async def __add(self: "ASyncFuture[int]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    async def __add(self: "ASyncFuture[Decimal]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    @overload
    async def __add(self: "ASyncFuture[Decimal]", other: "ASyncFuture[int]") -> "ASyncFuture[Decimal]":...
    @overload
    async def __add(self: "ASyncFuture[int]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    async def __add(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        return a + b
    @overload
    async def __sub(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]":...
    @overload
    async def __sub(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]":...
    @overload
    async def __sub(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]":...
    @overload
    async def __sub(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]":...
    @overload
    async def __sub(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    async def __sub(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]":...
    @overload
    async def __sub(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    async def __sub(self: "ASyncFuture[int]", other: "ASyncFuture[int]") -> "ASyncFuture[int]":...
    @overload
    async def __sub(self: "ASyncFuture[float]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    async def __sub(self: "ASyncFuture[float]", other: "ASyncFuture[int]") -> "ASyncFuture[float]":...
    @overload
    async def __sub(self: "ASyncFuture[int]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    async def __sub(self: "ASyncFuture[Decimal]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    @overload
    async def __sub(self: "ASyncFuture[Decimal]", other: "ASyncFuture[int]") -> "ASyncFuture[Decimal]":...
    @overload
    async def __sub(self: "ASyncFuture[int]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    async def __sub(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        return a - b
    async def __mul(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        return a * b
    async def __truediv(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        return a / b
    async def __floordiv(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        return a // b
    async def __pow(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        return a ** b
    
    # rMaths
    @overload
    async def __radd(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]":...
    @overload
    async def __radd(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]":...
    @overload
    async def __radd(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]":...
    @overload
    async def __radd(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]":...
    @overload
    async def __radd(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    async def __radd(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]":...
    @overload
    async def __radd(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    async def __radd(self: "ASyncFuture[int]", other: "ASyncFuture[int]") -> "ASyncFuture[int]":...
    @overload
    async def __radd(self: "ASyncFuture[float]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    async def __radd(self: "ASyncFuture[float]", other: "ASyncFuture[int]") -> "ASyncFuture[float]":...
    @overload
    async def __radd(self: "ASyncFuture[int]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    async def __radd(self: "ASyncFuture[Decimal]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    @overload
    async def __radd(self: "ASyncFuture[Decimal]", other: "ASyncFuture[int]") -> "ASyncFuture[Decimal]":...
    @overload
    async def __radd(self: "ASyncFuture[int]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    async def __radd(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(other, self)
        return a + b
    @overload
    async def __rsub(self: "ASyncFuture[int]", other: int) -> "ASyncFuture[int]":...
    @overload
    async def __rsub(self: "ASyncFuture[float]", other: float) -> "ASyncFuture[float]":...
    @overload
    async def __rsub(self: "ASyncFuture[float]", other: int) -> "ASyncFuture[float]":...
    @overload
    async def __rsub(self: "ASyncFuture[int]", other: float) -> "ASyncFuture[float]":...
    @overload
    async def __rsub(self: "ASyncFuture[Decimal]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    async def __rsub(self: "ASyncFuture[Decimal]", other: int) -> "ASyncFuture[Decimal]":...
    @overload
    async def __rsub(self: "ASyncFuture[int]", other: Decimal) -> "ASyncFuture[Decimal]":...
    @overload
    async def __rsub(self: "ASyncFuture[int]", other: "ASyncFuture[int]") -> "ASyncFuture[int]":...
    @overload
    async def __rsub(self: "ASyncFuture[float]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    async def __rsub(self: "ASyncFuture[float]", other: "ASyncFuture[int]") -> "ASyncFuture[float]":...
    @overload
    async def __rsub(self: "ASyncFuture[int]", other: "ASyncFuture[float]") -> "ASyncFuture[float]":...
    @overload
    async def __rsub(self: "ASyncFuture[Decimal]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    @overload
    async def __rsub(self: "ASyncFuture[Decimal]", other: "ASyncFuture[int]") -> "ASyncFuture[Decimal]":...
    @overload
    async def __rsub(self: "ASyncFuture[int]", other: "ASyncFuture[Decimal]") -> "ASyncFuture[Decimal]":...
    async def __rsub(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(other, self)
        return a - b
    async def __rmul(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(other, self)
        return a * b
    async def __rtruediv(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(other, self)
        return a / b
    async def __rfloordiv(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(other, self)
        return a // b
    async def __rpow(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(other, self)
        return a ** b
    
    async def __iadd(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        self._result = a + b
        return self._result
    async def __isub(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        self._result = a - b
        return self._result
    async def __imul(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        self._result = a * b
        return self._result
    async def __itruediv(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        self._result = a / b
        return self._result
    async def __ifloordiv(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        self._result = a // b
        return self._result
    async def __ipow(self, other) -> "Any":
        a, b = await _gather_check_and_materialize(self, other)
        self._result = a ** b
        return self._result
    
    # Comparisons
    async def __eq(self, other) -> bool:
        a, b = await _gather_check_and_materialize(self, other)
        return a == b
    async def __gt(self, other) -> bool:
        a, b = await _gather_check_and_materialize(self, other)
        return a > b
    async def __ge(self, other) -> bool:
        a, b = await _gather_check_and_materialize(self, other)
        return a >= b
    async def __lt(self, other) -> bool:
        a, b = await _gather_check_and_materialize(self, other)
        return a < b
    async def __le(self, other) -> bool:
        a, b = await _gather_check_and_materialize(self, other)
        return a <= b

    
    # not sure what to call these
    async def __contains(self, item: Any) -> bool:
        _self, _item = await _gather_check_and_materialize(self, item)
        return _item in _self
        
    # conversion
    # NOTE: We aren't allowed to return ASyncFutures here :(
    def __bool__(self) -> bool:
        return bool(_materialize(self))
    def __bytes__(self) -> bytes:
        return bytes(_materialize(self))
    def __str__(self) -> str:
        return str(_materialize(self))
    def __int__(self) -> int:
        return int(_materialize(self))
    def __float__(self) -> float:
        return float(_materialize(self))
      
class _ASyncFutureWrappedFn(Callable[P, ASyncFuture[T]]):
    __slots__ = "callable", "wrapped"
    def __init__(self, callable: Union[Callable[P, Awaitable[T]], Callable[P, T]] = None, **kwargs: Unpack[ModifierKwargs]):
        from a_sync import a_sync
        if callable:
            self.callable = callable
            a_sync_callable = a_sync(callable, default="async", **kwargs)
            @wraps(callable)
            def future_wrap(*args: P.args, **kwargs: P.kwargs) -> "ASyncFuture[T]":
                return ASyncFuture(a_sync_callable(*args, **kwargs, sync=False))
            self.wrapped = future_wrap
        else:
            self.wrapped = partial(_ASyncFutureWrappedFn, **kwargs)
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> ASyncFuture[T]:
        return self.wrapped(*args, **kwargs)
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.callable}>"
