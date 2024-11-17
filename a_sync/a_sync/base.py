import functools
import inspect
import logging
from contextlib import suppress

from a_sync import exceptions
from a_sync._typing import *
from a_sync.a_sync import _flags
from a_sync.a_sync.abstract import ASyncABC


logger = logging.getLogger(__name__)


class ASyncGenericBase(ASyncABC):
    """
    Base class for creating dual-function sync/async-capable classes without writing all your code twice.

    This class, via its inherited metaclass :class:`~ASyncMeta', provides the foundation for creating hybrid sync/async classes. It allows methods
    and properties to be defined once and used in both synchronous and asynchronous contexts.

    The class uses the :func:`a_sync` decorator internally to create dual-mode methods and properties.
    Subclasses should define their methods as coroutines (using `async def`) where possible, and
    use the `@a_sync.property` or `@a_sync.cached_property` decorators for properties that need to support both modes.

    Example:
        ```python
        class MyClass(ASyncGenericBase):
            def __init__(self, sync: bool):
                self.sync = sync

            @a_sync.property
            async def my_property(self):
                return await some_async_operation()

            @a_sync
            async def my_method(self):
                return await another_async_operation()

        # Synchronous usage
        obj = MyClass(sync=True)
        sync_result = obj.my_property
        sync_method_result = obj.my_method()

        # Asynchronous usage
        obj = MyClass(sync=False)
        async_result = await obj.my_property
        async_method_result = await obj.my_method()
        ```

    Note:
        When subclassing, be aware that all async methods and properties will be
        automatically wrapped to support both sync and async calls. This allows for
        seamless usage in different contexts without changing the underlying implementation.
    """

    def __init__(self):
        if type(self) is ASyncGenericBase:
            cls_name = type(self).__name__
            raise NotImplementedError(
                f"You should not create instances of `{cls_name}` directly, you should subclass `ASyncGenericBase` instead."
            )
        ASyncABC.__init__(self)

    @functools.cached_property
    def __a_sync_flag_name__(self) -> str:
        logger.debug("checking a_sync flag for %s", self)
        try:
            flag = self.__get_a_sync_flag_name_from_signature()
        except exceptions.ASyncFlagException:
            # We can't get the flag name from the __init__ signature,
            # but maybe the implementation sets the flag somewhere else.
            # Let's check the instance's atributes
            logger.debug(
                "unable to find flag name using `%s.__init__` signature, checking for flag attributes defined on %s",
                self.__class__.__name__,
                self,
            )
            present_flags = [
                flag for flag in _flags.VIABLE_FLAGS if hasattr(self, flag)
            ]
            if not present_flags:
                raise exceptions.NoFlagsFound(self) from None
            if len(present_flags) > 1:
                raise exceptions.TooManyFlags(self, present_flags) from None
            flag = present_flags[0]
        if not isinstance(flag, str):
            raise exceptions.InvalidFlag(flag)
        return flag

    @functools.cached_property
    def __a_sync_flag_value__(self) -> bool:
        """If you wish to be able to hotswap default modes, just duplicate this def as a non-cached property."""
        flag = self.__a_sync_flag_name__
        flag_value = getattr(self, flag)
        if not isinstance(flag_value, bool):
            raise exceptions.InvalidFlagValue(flag, flag_value)
        logger.debug("`%s.%s` is currently %s", self, flag, flag_value)
        return flag_value

    @classmethod  # type: ignore [misc]
    def __a_sync_default_mode__(cls) -> bool:  # type: ignore [override]
        try:
            flag = cls.__get_a_sync_flag_name_from_signature()
            flag_value = cls.__a_sync_flag_default_value_from_signature()
        except exceptions.NoFlagsFound:
            flag = cls.__get_a_sync_flag_name_from_class_def()
            flag_value = cls.__get_a_sync_flag_value_from_class_def(flag)
        sync = _flags.negate_if_necessary(flag, flag_value)  # type: ignore [arg-type]
        logger.debug(
            "`%s.%s` indicates default mode is %ssynchronous",
            cls,
            flag,
            "a" if sync is False else "",
        )
        return sync

    @classmethod
    def __get_a_sync_flag_name_from_signature(cls) -> Optional[str]:
        logger.debug("Searching for flags defined on %s.__init__", cls)
        if cls.__name__ == "ASyncGenericBase":
            logger.debug(
                "There are no flags defined on the base class, this is expected. Skipping."
            )
            return None
        parameters = inspect.signature(cls.__init__).parameters
        logger.debug("parameters: %s", parameters)
        return cls.__parse_flag_name_from_list(parameters)

    @classmethod
    def __get_a_sync_flag_name_from_class_def(cls) -> str:
        logger.debug("Searching for flags defined on %s", cls)
        try:
            return cls.__parse_flag_name_from_list(cls.__dict__)  # type: ignore [arg-type]
            # idk why __dict__ doesn't type check as a dict
        except exceptions.NoFlagsFound:
            for base in cls.__bases__:
                with suppress(exceptions.NoFlagsFound):
                    return cls.__parse_flag_name_from_list(base.__dict__)  # type: ignore [arg-type]
                    # idk why __dict__ doesn't type check as a dict
        raise exceptions.NoFlagsFound(cls, list(cls.__dict__.keys()))

    @classmethod  # type: ignore [misc]
    def __a_sync_flag_default_value_from_signature(cls) -> bool:
        logger.debug(
            "checking `__init__` signature for default %s a_sync flag value", cls
        )
        signature = inspect.signature(cls.__init__)
        flag = cls.__get_a_sync_flag_name_from_signature()
        flag_value = signature.parameters[flag].default
        if flag_value is inspect._empty:  # type: ignore [attr-defined]
            raise NotImplementedError(
                "The implementation for 'cls' uses an arg to specify sync mode, instead of a kwarg. We are unable to proceed. I suppose we can extend the code to accept positional arg flags if necessary"
            )
        logger.debug("%s defines %s, default value %s", cls, flag, flag_value)
        return flag_value

    @classmethod
    def __get_a_sync_flag_value_from_class_def(cls, flag: str) -> bool:
        for spec in [cls, *cls.__bases__]:
            if flag in spec.__dict__:
                return spec.__dict__[flag]
        raise exceptions.FlagNotDefined(cls, flag)

    @classmethod
    def __parse_flag_name_from_list(cls, items: Dict[str, Any]) -> str:
        present_flags = [flag for flag in _flags.VIABLE_FLAGS if flag in items]
        if not present_flags:
            logger.debug("There are too many flags defined on %s", cls)
            raise exceptions.NoFlagsFound(cls, items.keys())
        if len(present_flags) > 1:
            logger.debug("There are too many flags defined on %s", cls)
            raise exceptions.TooManyFlags(cls, present_flags)
        flag = present_flags[0]
        logger.debug("found flag %s", flag)
        return flag
