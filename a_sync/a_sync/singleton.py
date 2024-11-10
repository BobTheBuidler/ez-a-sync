from a_sync.a_sync._meta import ASyncSingletonMeta
from a_sync.a_sync.base import ASyncGenericBase


class ASyncGenericSingleton(ASyncGenericBase, metaclass=ASyncSingletonMeta):
    """
    A base class for creating singleton-esque ASync classes.

    This class combines the functionality of ASyncGenericBase with a singleton pattern,
    ensuring that only one instance of the class exists per execution mode (sync/async).
    It uses a custom metaclass to manage instance creation and caching.

    Subclasses of ASyncGenericSingleton will have two instances instead of one:
    - one synchronous instance
    - one asynchronous instance

    This allows for proper behavior in both synchronous and asynchronous contexts
    while maintaining the singleton pattern within each context.

    Example:
        class MyAsyncSingleton(ASyncGenericSingleton):
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
    """
