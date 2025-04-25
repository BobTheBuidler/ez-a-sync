from types import coroutine

@coroutine
def sleep0() -> None:
    yield
