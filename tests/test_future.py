
from a_sync.future import ASyncFuture


class StuffDoer:
    def do_stuff(self, smth=None):
        if smth:
            raise ValueError
        return 1

async def dct():
    return {1:2}

async def one() -> int:
    return 1

async def two() -> int:
    return 2

async def zero():
    return 0

def test_add():
    assert ASyncFuture(one()) + ASyncFuture(two()) == 3
    assert ASyncFuture(one()) + 2 == 3
    assert 1 + ASyncFuture(two()) == 3
def test_sum():
    assert sum([ASyncFuture(one()), ASyncFuture(two())]) == 3
    assert sum([ASyncFuture(one()), 2]) == 3
    assert sum([1, ASyncFuture(two())]) == 3
def test_sub():
    assert ASyncFuture(one()) - ASyncFuture(two()) == -1
    assert ASyncFuture(one()) - 2 == -1
    assert 1 - ASyncFuture(two()) == -1
def test_mul():
    assert ASyncFuture(one()) * ASyncFuture(two()) == 2
    assert ASyncFuture(one()) * 2 == 2
    assert 1 * ASyncFuture(two()) == 2
def test_pow():
    assert ASyncFuture(two()) ** ASyncFuture(two()) == 4
    assert ASyncFuture(two()) ** 2 == 4
    assert 2 ** ASyncFuture(two()) == 4
def test_realdiv():
    assert ASyncFuture(one()) / ASyncFuture(two()) == 0.5
    assert ASyncFuture(one()) / 2 == 0.5
    assert 1 / ASyncFuture(two()) == 0.5
def test_floordiv():
    assert ASyncFuture(one()) // ASyncFuture(two()) == 0
    assert ASyncFuture(one()) // 2 == 0
    assert 1 // ASyncFuture(two()) == 0
def test_gt():
    assert not ASyncFuture(one()) > ASyncFuture(two())
    assert ASyncFuture(two()) > ASyncFuture(one())
    assert not ASyncFuture(one()) > ASyncFuture(one())
def test_gte():
    assert not ASyncFuture(one()) >= ASyncFuture(two())
    assert ASyncFuture(two()) >= ASyncFuture(one())
    assert ASyncFuture(one()) >= ASyncFuture(one())
def test_lt():
    assert ASyncFuture(one()) < ASyncFuture(two())
    assert not ASyncFuture(two()) < ASyncFuture(one())
    assert not ASyncFuture(one()) < ASyncFuture(one())
def test_lte():
    assert ASyncFuture(one()) <= ASyncFuture(two())
    assert not ASyncFuture(two()) <= ASyncFuture(one())
    assert ASyncFuture(one()) <= ASyncFuture(one())
def test_bool():
    assert bool(ASyncFuture(one())) == True
    assert bool(ASyncFuture(zero())) == False
def test_float():
    assert float(ASyncFuture(one())) == float(1)
def test_str():
    assert str(ASyncFuture(one())) == "1"

def test_getitem():
    assert ASyncFuture(dct())[1] == 2

# NOTE: does not work
def test_setitem():
    meta = ASyncFuture(dct())
    print(meta)
    meta[3] = 4
    assert meta == {1:2, 3:4}
    assert meta[3] == 4
    
async def stuff_doer():
    return StuffDoer()

def test_getattr():
    assert ASyncFuture(stuff_doer()).do_stuff()

import pytest 

def test_multi_maths():
    some_cool_evm_value = ASyncFuture(two())
    scale = ASyncFuture(one())
    some = ASyncFuture(two())
    other = ASyncFuture(two())
    stuff = ASyncFuture(two())
    idrk = ASyncFuture(one())
    output0 = some_cool_evm_value / scale ** some # 2
    output1 = other + stuff - idrk # 3
    output = output0 * output1
    assert output0 < output1
    assert not output0 > output1
    assert isinstance(output, ASyncFuture)
    assert output0 == 2
    a = output0 * output1
    b = output1 * output0
    assert a == b
    assert output == 6
    with pytest.raises(ValueError):
        ASyncFuture(stuff_doer()).do_stuff(6)
        