
from a_sync.base import ASyncGenericBase
from a_sync._meta import ASyncSingletonMeta

class ASyncGenericSingleton(ASyncGenericBase, metaclass=ASyncSingletonMeta):
    pass
