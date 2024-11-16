from a_sync._typing import *
import abc
import functools
from _typeshed import Incomplete
from a_sync import exceptions as exceptions
from a_sync.a_sync import modifiers as modifiers
from a_sync.a_sync._meta import ASyncMeta as ASyncMeta
from a_sync.exceptions import NoFlagsFound as NoFlagsFound

logger: Incomplete

class ASyncABC(metaclass=ASyncMeta):
    """Abstract Base Class for defining asynchronous and synchronous behavior.

    This class provides methods to determine the execution mode based on flags and keyword arguments.
    It is designed to be subclassed, allowing developers to create classes that can be used in both
    synchronous and asynchronous contexts.

    See Also:
        - :class:`ASyncGenericBase`: A more user-friendly base class for creating dual-mode classes.
        - :class:`ASyncMeta`: Metaclass that facilitates asynchronous capabilities in class attributes.

    Examples:
        To create a class that inherits from `ASyncABC`, you need to implement the abstract methods
        and can override the concrete methods if needed.

        ```python
        class MyASyncClass(ASyncABC):
            @property
            def __a_sync_flag_name__(self) -> str:
                return "sync"

            @property
            def __a_sync_flag_value__(self) -> bool:
                return True

            @classmethod
            def __a_sync_default_mode__(cls) -> bool:
                return False
        ```

        In this example, `MyASyncClass` is a subclass of `ASyncABC` with custom implementations
        for the required abstract methods.
    """

    def __a_sync_should_await__(self, kwargs: dict) -> bool:
        """Determines if methods should be called asynchronously.

        This method first checks the provided keyword arguments for flags
        indicating the desired execution mode. If no flags are found, it
        defaults to the instance's asynchronous flag.

        Args:
            kwargs: A dictionary of keyword arguments to check for flags.

        Examples:
            >>> instance = MyASyncClass()
            >>> instance.__a_sync_should_await__({'sync': True})
            False
        """

    @functools.cached_property
    def __a_sync_instance_should_await__(self) -> bool:
        """Indicates if the instance should default to asynchronous execution.

        This property can be overridden if dynamic behavior is needed. For
        instance, to allow hot-swapping of instance modes, redefine this as a
        non-cached property.

        Examples:
            >>> instance = MyASyncClass()
            >>> instance.__a_sync_instance_should_await__
            True
        """

    def __a_sync_should_await_from_kwargs__(self, kwargs: dict) -> bool:
        """Determines execution mode from keyword arguments.

        This method can be overridden to customize how flags are extracted
        from keyword arguments.

        Args:
            kwargs: A dictionary of keyword arguments to check for flags.

        Raises:
            NoFlagsFound: If no valid flags are found in the keyword arguments.

        Examples:
            >>> instance = MyASyncClass()
            >>> instance.__a_sync_should_await_from_kwargs__({'sync': False})
            True
        """

    @classmethod
    def __a_sync_instance_will_be_sync__(cls, args: tuple, kwargs: dict) -> bool:
        """Determines if a new instance will be synchronous.

        This method checks the constructor's signature against provided
        keyword arguments to determine the execution mode for the new instance.

        Args:
            args: A tuple of positional arguments for the instance.
            kwargs: A dictionary of keyword arguments for the instance.

        Examples:
            >>> MyASyncClass.__a_sync_instance_will_be_sync__((), {'sync': True})
            True
        """

    @property
    def __a_sync_modifiers__(self) -> ModifierKwargs:
        """Retrieves modifiers for the instance.

        This method should not be overridden. It returns the modifiers
        associated with the instance, which are used to customize behavior.

        Examples:
            >>> instance = MyASyncClass()
            >>> instance.__a_sync_modifiers__
            {'cache_type': 'memory'}
        """

    @property
    @abc.abstractmethod
    def __a_sync_flag_name__(self) -> str:
        """Abstract property for the flag name.

        Subclasses must implement this property to return the name of the flag
        used to determine execution mode.
        """

    @property
    @abc.abstractmethod
    def __a_sync_flag_value__(self) -> bool:
        """Abstract property for the flag value.

        Subclasses must implement this property to return the value of the flag
        indicating the default execution mode.
        """

    @classmethod
    @abc.abstractmethod
    def __a_sync_default_mode__(cls) -> bool:
        """Abstract class method for the default execution mode.

        Subclasses must implement this method to return the default execution
        mode (synchronous or asynchronous) for instances of the class.
        """
