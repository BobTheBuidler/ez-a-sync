# cython: profile=False
# cython: linetrace=False

from types import coroutine

@coroutine
def sleep0():
    yield
