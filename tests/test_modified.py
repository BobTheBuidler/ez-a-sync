import a_sync


@a_sync.a_sync
def sync_def():
    pass


@a_sync.a_sync
async def async_def():
    pass


def test_sync_def_repr():
    assert sync_def.__name__ == "sync_def"


def test_async_def_repr():
    assert async_def.__name__ == "async_def"
