from a_sync._typing import *
import async_property as ap
from _typeshed import Incomplete
from a_sync import exceptions as exceptions
from a_sync.a_sync import config as config
from a_sync.a_sync._descriptor import ASyncDescriptor as ASyncDescriptor
from a_sync.a_sync.function import (
    ASyncFunction as ASyncFunction,
    ASyncFunctionAsyncDefault as ASyncFunctionAsyncDefault,
    ASyncFunctionSyncDefault as ASyncFunctionSyncDefault,
)
from a_sync.a_sync.method import (
    ASyncBoundMethodAsyncDefault as ASyncBoundMethodAsyncDefault,
    ASyncMethodDescriptorAsyncDefault as ASyncMethodDescriptorAsyncDefault,
)
from a_sync.task import TaskMapping as TaskMapping
from collections.abc import Generator
from typing import Any
from typing_extensions import Unpack

logger: Incomplete

class _ASyncPropertyDescriptorBase(ASyncDescriptor[I, Tuple[()], T]):
    """Base class for creating asynchronous properties.

    This class provides the foundation for defining properties that can be accessed
    both synchronously and asynchronously. It includes utility methods for common
    operations such as `any`, `all`, `min`, `max`, and `sum`.
    """

    any: ASyncFunction[AnyIterable[I], bool]
    all: ASyncFunction[AnyIterable[I], bool]
    min: ASyncFunction[AnyIterable[I], T]
    max: ASyncFunction[AnyIterable[I], T]
    sum: ASyncFunction[AnyIterable[I], T]
    hidden_method_descriptor: HiddenMethodDescriptor[T]
    __wrapped__: Callable[[I], T]
    hidden_method_name: Incomplete
    def __init__(
        self,
        _fget: AsyncGetterFunction[I, T],
        field_name: Optional[str] = None,
        **modifiers: Unpack[ModifierKwargs]
    ) -> None:
        """Initializes the _ASyncPropertyDescriptorBase.

        Args:
            _fget: The function to be wrapped.
            field_name: Optional name for the field. If not provided, the function's name will be used.
            **modifiers: Additional modifier arguments.
        """

    @overload
    def __get__(self, instance: None, owner: Type[I]) -> Self: ...
    @overload
    def __get__(self, instance: I, owner: Type[I]) -> Awaitable[T]: ...
    async def get(self, instance: I, owner: Optional[Type[I]] = None) -> T:
        """Asynchronously retrieves the property value.

        Args:
            instance: The instance from which the property is accessed.
            owner: The owner class of the property.

        Returns:
            The property value.
        """

    def map(
        self,
        instances: AnyIterable[I],
        owner: Optional[Type[I]] = None,
        concurrency: Optional[int] = None,
        name: str = "",
    ) -> TaskMapping[I, T]:
        """Maps the property across multiple instances.

        Args:
            instances: An iterable of instances.
            owner: The owner class of the property.
            concurrency: Optional concurrency limit.
            name: Optional name for the task mapping.

        Returns:
            A TaskMapping object.
        """

class ASyncPropertyDescriptor(_ASyncPropertyDescriptorBase[I, T], ap.base.AsyncPropertyDescriptor):
    """Descriptor class for asynchronous properties."""

class ASyncPropertyDescriptorSyncDefault(ASyncPropertyDescriptor[I, T]):
    """
    A variant of :class:`~ASyncPropertyDescriptor` that defaults to synchronous behavior.

    This class is used when the property is primarily intended to be accessed
    synchronously but can also be used asynchronously if needed.
    """

    default: str
    any: ASyncFunctionSyncDefault[AnyIterable[I], bool]
    all: ASyncFunctionSyncDefault[AnyIterable[I], bool]
    min: ASyncFunctionSyncDefault[AnyIterable[I], T]
    max: ASyncFunctionSyncDefault[AnyIterable[I], T]
    sum: ASyncFunctionSyncDefault[AnyIterable[I], T]
    @overload
    def __get__(self, instance: None, owner: Type[I]) -> Self: ...
    @overload
    def __get__(self, instance: I, owner: Type[I]) -> T: ...
    __get__: Incomplete

class ASyncPropertyDescriptorAsyncDefault(ASyncPropertyDescriptor[I, T]):
    """
    A variant of :class:`~ASyncPropertyDescriptor` that defaults to asynchronous behavior.

    This class is used when the property is primarily intended to be accessed
    asynchronously but can also be used synchronously if needed.
    """

    default: str
    any: ASyncFunctionAsyncDefault[AnyIterable[I], bool]
    all: ASyncFunctionAsyncDefault[AnyIterable[I], bool]
    min: ASyncFunctionAsyncDefault[AnyIterable[I], T]
    max: ASyncFunctionAsyncDefault[AnyIterable[I], T]
    sum: ASyncFunctionAsyncDefault[AnyIterable[I], T]

ASyncPropertyDecorator = Callable[[AnyGetterFunction[I, T]], ASyncPropertyDescriptor[I, T]]
ASyncPropertyDecoratorSyncDefault = Callable[
    [AnyGetterFunction[I, T]], ASyncPropertyDescriptorSyncDefault[I, T]
]
ASyncPropertyDecoratorAsyncDefault = Callable[
    [AnyGetterFunction[I, T]], ASyncPropertyDescriptorAsyncDefault[I, T]
]

@overload
def a_sync_property(
    func: Literal[None] = None, **modifiers: Unpack[ModifierKwargs]
) -> ASyncPropertyDecorator[I, T]: ...
@overload
def a_sync_property(
    func: AnyGetterFunction[I, T], **modifiers: Unpack[ModifierKwargs]
) -> ASyncPropertyDescriptor[I, T]: ...
@overload
def a_sync_property(
    func: Literal[None], default: Literal["sync"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncPropertyDecoratorSyncDefault[I, T]: ...
@overload
def a_sync_property(
    func: Literal[None], default: Literal["sync"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncPropertyDecoratorSyncDefault[I, T]: ...
@overload
def a_sync_property(
    func: Literal[None], default: Literal["async"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncPropertyDecoratorAsyncDefault[I, T]: ...
@overload
def a_sync_property(
    func: Literal[None], default: DefaultMode = ..., **modifiers: Unpack[ModifierKwargs]
) -> ASyncPropertyDecorator[I, T]: ...
@overload
def a_sync_property(
    default: Literal["sync"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncPropertyDecoratorSyncDefault[I, T]: ...
@overload
def a_sync_property(
    default: Literal["async"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncPropertyDecoratorAsyncDefault[I, T]: ...
@overload
def a_sync_property(
    func: AnyGetterFunction[I, T], default: Literal["sync"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncPropertyDescriptorSyncDefault[I, T]: ...
@overload
def a_sync_property(
    func: AnyGetterFunction[I, T], default: Literal["async"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncPropertyDescriptorAsyncDefault[I, T]: ...
@overload
def a_sync_property(
    func: AnyGetterFunction[I, T], default: DefaultMode = ..., **modifiers: Unpack[ModifierKwargs]
) -> ASyncPropertyDescriptor[I, T]: ...

class ASyncCachedPropertyDescriptor(
    _ASyncPropertyDescriptorBase[I, T], ap.cached.AsyncCachedPropertyDescriptor
):
    """
    A descriptor class for dual-function sync/async cached properties.

    This class extends the API of ASyncPropertyDescriptor to provide
    caching functionality, storing the computed value after the first access.
    """

    def __init__(
        self,
        _fget: AsyncGetterFunction[I, T],
        _fset: Incomplete | None = None,
        _fdel: Incomplete | None = None,
        field_name: Incomplete | None = None,
        **modifiers: Unpack[ModifierKwargs]
    ) -> None:
        """Initializes the ASyncCachedPropertyDescriptor.

        Args:
            _fget: The function to be wrapped.
            _fset: Optional setter function for the property.
            _fdel: Optional deleter function for the property.
            field_name: Optional name for the field. If not provided, the function's name will be used.
            **modifiers: Additional modifier arguments.
        """

    def get_lock(self, instance: I) -> asyncio.Task[T]:
        """Retrieves the lock for the property.

        Args:
            instance: The instance from which the property is accessed.

        Returns:
            An asyncio Task representing the lock.
        """

    def pop_lock(self, instance: I) -> None:
        """Removes the lock for the property.

        Args:
            instance: The instance from which the property is accessed.
        """

    def get_loader(self, instance: I) -> Callable[[], T]:
        """Retrieves the loader function for the property.

        Args:
            instance: The instance from which the property is accessed.

        Returns:
            A callable that loads the property value.
        """

class ASyncCachedPropertyDescriptorSyncDefault(ASyncCachedPropertyDescriptor[I, T]):
    """
    A variant of :class:`~ASyncCachedPropertyDescriptor` that defaults to synchronous behavior.

    This class is used for cached properties that are primarily intended to be
    accessed synchronously but can also be used asynchronously if needed.
    """

    default: Literal["sync"]
    @overload
    def __get__(self, instance: None, owner: Type[I]) -> Self: ...
    @overload
    def __get__(self, instance: I, owner: Type[I]) -> T: ...
    __get__: Incomplete

class ASyncCachedPropertyDescriptorAsyncDefault(ASyncCachedPropertyDescriptor[I, T]):
    """
    A variant of :class:`~ASyncCachedPropertyDescriptor` that defaults to asynchronous behavior.

    This class is used for cached properties that are primarily intended to be
    accessed asynchronously but can also be used synchronously if needed.
    """

    default: Literal["async"]

ASyncCachedPropertyDecorator = Callable[
    [AnyGetterFunction[I, T]], ASyncCachedPropertyDescriptor[I, T]
]
ASyncCachedPropertyDecoratorSyncDefault = Callable[
    [AnyGetterFunction[I, T]], ASyncCachedPropertyDescriptorSyncDefault[I, T]
]
ASyncCachedPropertyDecoratorAsyncDefault = Callable[
    [AnyGetterFunction[I, T]], ASyncCachedPropertyDescriptorAsyncDefault[I, T]
]

@overload
def a_sync_cached_property(
    func: Literal[None] = None, **modifiers: Unpack[ModifierKwargs]
) -> ASyncCachedPropertyDecorator[I, T]: ...
@overload
def a_sync_cached_property(
    func: AnyGetterFunction[I, T], **modifiers: Unpack[ModifierKwargs]
) -> ASyncCachedPropertyDescriptor[I, T]: ...
@overload
def a_sync_cached_property(
    func: Literal[None], default: Literal["sync"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncCachedPropertyDecoratorSyncDefault[I, T]: ...
@overload
def a_sync_cached_property(
    func: Literal[None], default: Literal["async"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncCachedPropertyDecoratorAsyncDefault[I, T]: ...
@overload
def a_sync_cached_property(
    func: Literal[None], default: DefaultMode, **modifiers: Unpack[ModifierKwargs]
) -> ASyncCachedPropertyDecorator[I, T]: ...
@overload
def a_sync_cached_property(
    default: Literal["sync"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncCachedPropertyDecoratorSyncDefault[I, T]: ...
@overload
def a_sync_cached_property(
    default: Literal["async"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncCachedPropertyDecoratorAsyncDefault[I, T]: ...
@overload
def a_sync_cached_property(
    func: AnyGetterFunction[I, T], default: Literal["sync"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncCachedPropertyDescriptorSyncDefault[I, T]: ...
@overload
def a_sync_cached_property(
    func: AnyGetterFunction[I, T], default: Literal["async"], **modifiers: Unpack[ModifierKwargs]
) -> ASyncCachedPropertyDescriptorAsyncDefault[I, T]: ...
@overload
def a_sync_cached_property(
    func: AnyGetterFunction[I, T], default: DefaultMode = ..., **modifiers: Unpack[ModifierKwargs]
) -> ASyncCachedPropertyDescriptor[I, T]: ...

class HiddenMethod(ASyncBoundMethodAsyncDefault[I, Tuple[()], T]):
    """Represents a hidden method for asynchronous properties.

    This class is used internally to manage hidden methods associated with
    asynchronous properties.
    """

    def __init__(
        self,
        instance: I,
        unbound: AnyFn[Concatenate[I, P], T],
        async_def: bool,
        field_name: str,
        **modifiers: Unpack[ModifierKwargs]
    ) -> None:
        """Initializes the HiddenMethod.

        Args:
            instance: The instance to which the method is bound.
            unbound: The unbound function to be wrapped.
            async_def: Indicates if the method is asynchronous.
            field_name: The name of the field associated with the method.
            **modifiers: Additional modifier arguments.
        """

    def __await__(self) -> Generator[Any, None, T]:
        """Returns an awaitable for the method."""

class HiddenMethodDescriptor(ASyncMethodDescriptorAsyncDefault[I, Tuple[()], T]):
    """Descriptor for hidden methods associated with asynchronous properties.

    This class is used internally to manage hidden methods associated with
    asynchronous properties.
    """

    __doc__: Incomplete
    def __init__(
        self,
        _fget: AnyFn[Concatenate[I, P], Awaitable[T]],
        field_name: Optional[str] = None,
        **modifiers: Unpack[ModifierKwargs]
    ) -> None:
        """
        Initialize the HiddenMethodDescriptor.

        Args:
            _fget: The function to be wrapped.
            field_name: Optional name for the field. If not provided, the function's name will be used.
            **modifiers: Additional modifier arguments.

        Raises:
            ValueError: If _fget is not callable.
        """

    def __get__(self, instance: I, owner: Type[I]) -> HiddenMethod[I, T]:
        """Retrieves the hidden method for the property.

        Args:
            instance: The instance from which the method is accessed.
            owner: The owner class of the method.

        Returns:
            The hidden method.
        """
