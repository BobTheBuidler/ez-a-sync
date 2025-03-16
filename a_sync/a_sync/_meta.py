import logging
import threading
from abc import ABCMeta
from inspect import isasyncgenfunction
from typing import Any, Dict, Tuple

from a_sync import ENVIRONMENT_VARIABLES
from a_sync.a_sync import modifiers
from a_sync.a_sync.function import ASyncFunction, _ModifiedMixin
from a_sync.a_sync.method import ASyncMethodDescriptor
from a_sync.a_sync.property import (
    ASyncCachedPropertyDescriptor,
    ASyncPropertyDescriptor,
)
from a_sync.future import _ASyncFutureWrappedFn  # type: ignore [attr-defined]
from a_sync.iter import ASyncGeneratorFunction
from a_sync.primitives.locks.semaphore import Semaphore

logger = logging.getLogger(__name__)


class ASyncMeta(ABCMeta):
    """Metaclass for wrapping class attributes with asynchronous capabilities.

    Any class with `ASyncMeta` as its metaclass will have its functions and properties
    wrapped with asynchronous capabilities upon class instantiation. This includes
    wrapping functions with :class:`~a_sync.a_sync.method.ASyncMethodDescriptor` and properties with
    :class:`~a_sync.a_sync.property.ASyncPropertyDescriptor` or :class:`~a_sync.a_sync.property.ASyncCachedPropertyDescriptor`.
    It also handles attributes that are instances of :class:`~a_sync.a_sync.function.ASyncFunction`,
    which are used when functions are decorated with a_sync decorators to apply specific modifiers to those functions.

    Attributes that are instances of :class:`~a_sync.future._ASyncFutureWrappedFn` and :class:`~a_sync.primitives.locks.semaphore.Semaphore`
    are explicitly skipped and not wrapped.

    Example:
        To create a class with asynchronous capabilities, define your class with `ASyncMeta` as its metaclass:

        >>> class MyClass(metaclass=ASyncMeta):
        ...     def my_method(self):
        ...         return "Hello, World!"

        The `my_method` function will be wrapped with :class:`~a_sync.a_sync.method.ASyncMethodDescriptor`, allowing it to be used asynchronously.

    See Also:
        - :class:`~a_sync.a_sync.function.ASyncFunction`
        - :class:`~a_sync.a_sync.method.ASyncMethodDescriptor`
        - :class:`~a_sync.a_sync.property.ASyncPropertyDescriptor`
        - :class:`~a_sync.a_sync.property.ASyncCachedPropertyDescriptor`
    """

    def __new__(cls, new_class_name, bases, attrs):
        _update_logger(new_class_name)
        logger.debug(
            "woah, you're defining a new ASync class `%s`! let's walk thru it together",
            new_class_name,
        )
        logger.debug(
            "first, I check whether you've defined any modifiers on `%s`",
            new_class_name,
        )
        # NOTE: Open quesion: what do we do when a parent class and subclass define the same modifier differently?
        #       Currently the parent value is used for functions defined on the parent,
        #       and the subclass value is used for functions defined on the subclass.
        class_defined_modifiers = modifiers.get_modifiers_from(attrs)

        logger.debug("found modifiers: %s", class_defined_modifiers)
        logger.debug(
            "now I inspect the class definition to figure out which attributes need to be wrapped"
        )
        for attr_name, attr_value in list(attrs.items()):
            if attr_name.startswith("_"):
                logger.debug(
                    "`%s.%s` starts with an underscore, skipping",
                    new_class_name,
                    attr_name,
                )
                continue
            elif "__" in attr_name:
                logger.debug(
                    "`%s.%s` incluldes a double-underscore, skipping",
                    new_class_name,
                    attr_name,
                )
                continue
            elif isinstance(attr_value, (_ASyncFutureWrappedFn, Semaphore)):
                logger.debug(
                    "`%s.%s` is a %s, skipping",
                    new_class_name,
                    attr_name,
                    attr_value.__class__.__name__,
                )
                continue
            logger.debug(
                f"inspecting `{new_class_name}.{attr_name}` of type {attr_value.__class__.__name__}"
            )
            fn_modifiers = dict(class_defined_modifiers)
            # Special handling for functions decorated with a_sync decorators
            if isinstance(attr_value, _ModifiedMixin):
                logger.debug(
                    "`%s.%s` is a `%s` object, which means you decorated it with an a_sync decorator even though `%s` is an ASyncABC class",
                    new_class_name,
                    attr_name,
                    type(attr_value).__name__,
                    new_class_name,
                )
                logger.debug(
                    "you probably did this so you could apply some modifiers to `%s` specifically",
                    attr_name,
                )
                if modified_modifiers := attr_value.modifiers._modifiers:
                    logger.debug(
                        "I found `%s.%s` is modified with %s",
                        new_class_name,
                        attr_name,
                        modified_modifiers,
                    )
                    fn_modifiers.update(modified_modifiers)
                else:
                    logger.debug("I did not find any modifiers")
                logger.debug(
                    "full modifier set for `%s.%s`: %s",
                    new_class_name,
                    attr_name,
                    fn_modifiers,
                )
                if isinstance(attr_value, (ASyncPropertyDescriptor, ASyncCachedPropertyDescriptor)):
                    # Wrap property
                    logger.debug("`%s is a property, now let's wrap it", attr_name)
                    logger.debug(
                        "since `%s` is a property, we will add a hidden dundermethod so you can still access it both sync and async",
                        attr_name,
                    )
                    attrs[attr_value.hidden_method_name] = attr_value.hidden_method_descriptor
                    logger.debug(
                        "`%s.%s` is now %s",
                        new_class_name,
                        attr_value.hidden_method_name,
                        attr_value.hidden_method_descriptor,
                    )
                elif isinstance(attr_value, ASyncFunction):
                    attrs[attr_name] = ASyncMethodDescriptor(attr_value, **fn_modifiers)
                else:
                    raise NotImplementedError(attr_name, attr_value)
            elif isasyncgenfunction(attr_value):
                attrs[attr_name] = ASyncGeneratorFunction(attr_value)
            elif callable(attr_value):
                # NOTE We will need to improve this logic if somebody needs to use it with classmethods or staticmethods.
                attrs[attr_name] = ASyncMethodDescriptor(attr_value, **fn_modifiers)
            else:
                logger.debug(
                    "`%s.%s` is not callable, we will take no action with it",
                    new_class_name,
                    attr_name,
                )
        return super(ASyncMeta, cls).__new__(cls, new_class_name, bases, attrs)


class ASyncSingletonMeta(ASyncMeta):
    """Metaclass for creating singleton instances with asynchronous capabilities.

    This metaclass extends :class:`~a_sync.a_sync._meta.ASyncMeta` to ensure that only one instance of a class
    is created for each synchronous or asynchronous context.

    Example:
        To create a singleton class with asynchronous capabilities, define your class with `ASyncSingletonMeta` as its metaclass:

        >>> class MySingleton(metaclass=ASyncSingletonMeta):
        ...     def __init__(self):
        ...         print("Instance created")

        The `MySingleton` class will ensure that only one instance is created for each context.

    See Also:
        - :class:`~a_sync.a_sync._meta.ASyncMeta`
    """

    def __init__(cls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any]) -> None:
        cls.__instances: Dict[bool, object] = {}
        """Dictionary to store singleton instances."""
        cls.__lock = threading.Lock()
        """Lock to ensure thread-safe instance creation."""

    def __call__(cls, *args: Any, **kwargs: Any):
        is_sync = cls.__a_sync_instance_will_be_sync__(args, kwargs)  # type: ignore [attr-defined]
        if is_sync not in cls.__instances:
            with cls.__lock:
                # Check again in case `__instance` was set while we were waiting for the lock.
                if is_sync not in cls.__instances:
                    cls.__instances[is_sync] = ASyncMeta.__call__(cls, *args, **kwargs)
        return cls.__instances[is_sync]


def _update_logger(new_class_name: str) -> None:
    """Update the logger configuration based on environment variables.

    Args:
        new_class_name: The name of the new class being created.
    """
    if ENVIRONMENT_VARIABLES.DEBUG_MODE or ENVIRONMENT_VARIABLES.DEBUG_CLASS_NAME == new_class_name:
        logger.addHandler(_debug_handler)
        logger.setLevel(logging.DEBUG)
        logger.info("debug mode activated")
    else:
        logger.removeHandler(_debug_handler)
        logger.setLevel(logging.INFO)


_debug_handler = logging.StreamHandler()

__all__ = ["ASyncMeta", "ASyncSingletonMeta"]
