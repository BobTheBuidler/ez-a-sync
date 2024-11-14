from a_sync.a_sync._meta import ASyncSingletonMeta
from a_sync.a_sync.base import ASyncGenericBase


class ASyncGenericSingleton(ASyncGenericBase, metaclass=ASyncSingletonMeta):
    """
    A base class for creating singleton-esque ASync classes.

    This class combines the functionality of :class:`ASyncGenericBase` with a singleton pattern,
    ensuring that only one instance of the class exists per execution mode (sync/async).
    It uses a custom metaclass :class:`ASyncSingletonMeta` to manage instance creation and caching.

    Subclasses of :class:`ASyncGenericSingleton` will have two instances instead of one:
    - one synchronous instance
    - one asynchronous instance

    This allows for proper behavior in both synchronous and asynchronous contexts
    while maintaining the singleton pattern within each context.

    Note:
        This class can be instantiated directly, but it is intended to be subclassed
        to define specific asynchronous behavior. Subclasses should define
        the necessary properties and methods to specify the asynchronous behavior, as outlined
        in :class:`ASyncGenericBase`.

    Example:
        Create a subclass of `ASyncGenericSingleton` to define specific behavior:

        .. code-block:: python

            class MyAsyncSingleton(ASyncGenericSingleton):
                @property
                def __a_sync_flag_name__(self):
                    return "asynchronous"

                @property
                def __a_sync_flag_value__(self):
                    return self.asynchronous

                @classmethod
                def __a_sync_default_mode__(cls):
                    return False

                @a_sync
                def my_method(self):
                    # Method implementation

            # These will return the same synchronous instance
            sync_instance1 = MyAsyncSingleton(sync=True)
            sync_instance2 = MyAsyncSingleton(sync=True)

            # These will return the same asynchronous instance
            async_instance1 = MyAsyncSingleton(asynchronous=True)
            async_instance2 = MyAsyncSingleton(asynchronous=True)

            assert sync_instance1 is sync_instance2
            assert async_instance1 is async_instance2
            assert sync_instance1 is not async_instance1

    See Also:
        - :class:`ASyncGenericBase` for base functionality.
        - :class:`ASyncSingletonMeta` for the metaclass managing the singleton behavior.
    """
