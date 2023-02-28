
import async_property
from a_sync.semaphores import dummy_semaphore as dummy

# Aiases for async_property lib
property = async_property.async_property
cached_property = async_property.async_cached_property
