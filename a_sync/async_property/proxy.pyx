
import operator
cdef object index = operator.index
cdef object truediv = operator.truediv
cdef object itruediv = operator.itruediv
del operator

cdef class AwaitableOnly:
    """This wraps a coroutine will call it on await."""

    def __cinit__(self, object coro):
        self._coro = coro

    def __repr__(self):
        return f'<AwaitableOnly "{self._coro.__qualname__}">'

    def __await__(self):
        return self._coro().__await__()


# PURE PYTHON
"""Below taken from: https://github.com/GrahamDumpleton/wrapt/blob/master/src/wrapt/wrappers.py

Copyright (c) 2013-2019, Graham Dumpleton
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""


class _ObjectProxyMethods(object):

    # We use properties to override the values of __module__ and
    # __doc__. If we add these in ObjectProxy, the derived class
    # __dict__ will still be setup to have string variants of these
    # attributes and the rules of descriptors means that they appear to
    # take precedence over the properties in the base class. To avoid
    # that, we copy the properties into the derived class type itself
    # via a meta class. In that way the properties will always take
    # precedence.

    @property
    def __module__(self):
        return self.__wrapped__.__module__

    @__module__.setter
    def __module__(self, value):
        self.__wrapped__.__module__ = value

    @property
    def __doc__(self):
        return self.__wrapped__.__doc__

    @__doc__.setter
    def __doc__(self, value):
        self.__wrapped__.__doc__ = value

    # We similar use a property for __dict__. We need __dict__ to be
    # explicit to ensure that vars() works as expected.

    @property
    def __dict__(self):
        return self.__wrapped__.__dict__

    # Need to also propagate the special __weakref__ attribute for case
    # where decorating classes which will define this. If do not define
    # it and use a function like inspect.getmembers() on a decorator
    # class it will fail. This can't be in the derived classes.

    @property
    def __weakref__(self):
        return self.__wrapped__.__weakref__


class _ObjectProxyMetaType(type):
    def __new__(cls, name, bases, dictionary):
        # Copy our special properties into the class so that they
        # always take precedence over attributes of the same name added
        # during construction of a derived class. This is to save
        # duplicating the implementation for them in all derived classes.

        dictionary.update(vars(_ObjectProxyMethods))

        return type.__new__(cls, name, bases, dictionary)


cdef object _setattr = object.__setattr__
cdef object _delattr = object.__delattr__

class ObjectProxy(metaclass=_ObjectProxyMetaType):

    __slots__ = '__wrapped__'

    def __init__(self, wrapped):
        _setattr(self, '__wrapped__', wrapped)

        # Python 3.2+ has the __qualname__ attribute, but it does not
        # allow it to be overridden using a property and it must instead
        # be an actual string object instead.

        # We are skipping the below code block that was in the original implementation due to
        # results of my profiling and the fact that it isn't really relevant for most users.
        """
        try:
            _setattr(self, '__qualname__', wrapped.__qualname__)
        except AttributeError:
            pass
        """

    @property
    def __name__(self):
        return self.__wrapped__.__name__

    @__name__.setter
    def __name__(self, value):
        self.__wrapped__.__name__ = value

    @property
    def __class__(self):
        return self.__wrapped__.__class__

    @__class__.setter
    def __class__(self, value):
        self.__wrapped__.__class__ = value

    @property
    def __annotations__(self):
        return self.__wrapped__.__annotations__

    @__annotations__.setter
    def __annotations__(self, value):
        self.__wrapped__.__annotations__ = value

    def __dir__(self):
        return dir(self.__wrapped__)

    def __str__(self):
        return str(self.__wrapped__)

    def __bytes__(self):
        return bytes(self.__wrapped__)

    def __repr__(self):
        return '<{} at 0x{:x} for {} at 0x{:x}>'.format(
                type(self).__name__, id(self),
                type(self.__wrapped__).__name__,
                id(self.__wrapped__))

    def __reversed__(self):
        return reversed(self.__wrapped__)

    def __round__(self):
        return round(self.__wrapped__)

    def __lt__(self, other):
        return self.__wrapped__ < other

    def __le__(self, other):
        return self.__wrapped__ <= other

    def __eq__(self, other):
        return self.__wrapped__ == other

    def __ne__(self, other):
        return self.__wrapped__ != other

    def __gt__(self, other):
        return self.__wrapped__ > other

    def __ge__(self, other):
        return self.__wrapped__ >= other

    def __hash__(self):
        return hash(self.__wrapped__)

    def __bool__(self):
        return bool(self.__wrapped__)

    def __setattr__(self, name, value):
        if name.startswith('_self_'):
            _setattr(self, name, value)

        elif name == '__wrapped__':
            _setattr(self, name, value)
            try:
                _delattr(self, '__qualname__')
            except AttributeError:
                pass
            try:
                _setattr(self, '__qualname__', value.__qualname__)
            except AttributeError:
                pass

        elif name == '__qualname__':
            setattr(self.__wrapped__, name, value)
            _setattr(self, name, value)

        elif hasattr(type(self), name):
            _setattr(self, name, value)

        else:
            setattr(self.__wrapped__, name, value)

    def __getattr__(self, name):
        # If we are being to lookup '__wrapped__' then the
        # '__init__()' method cannot have been called.

        if name == '__wrapped__':
            raise ValueError('wrapper has not been initialised')

        return getattr(self.__wrapped__, name)

    def __delattr__(self, name):
        if name.startswith('_self_'):
            _delattr(self, name)

        elif name == '__wrapped__':
            raise TypeError('__wrapped__ must be an object')

        elif name == '__qualname__':
            _delattr(self, name)
            delattr(self.__wrapped__, name)

        elif hasattr(type(self), name):
            _delattr(self, name)

        else:
            delattr(self.__wrapped__, name)

    def __add__(self, other):
        return self.__wrapped__ + other

    def __sub__(self, other):
        return self.__wrapped__ - other

    def __mul__(self, other):
        return self.__wrapped__ * other

    def __truediv__(self, other):
        return truediv(self.__wrapped__, other)

    def __floordiv__(self, other):
        return self.__wrapped__ // other

    def __mod__(self, other):
        return self.__wrapped__ % other

    def __divmod__(self, other):
        return divmod(self.__wrapped__, other)

    def __pow__(self, other, *args):
        return pow(self.__wrapped__, other, *args)

    def __lshift__(self, other):
        return self.__wrapped__ << other

    def __rshift__(self, other):
        return self.__wrapped__ >> other

    def __and__(self, other):
        return self.__wrapped__ & other

    def __xor__(self, other):
        return self.__wrapped__ ^ other

    def __or__(self, other):
        return self.__wrapped__ | other

    def __radd__(self, other):
        return other + self.__wrapped__

    def __rsub__(self, other):
        return other - self.__wrapped__

    def __rmul__(self, other):
        return other * self.__wrapped__

    def __rtruediv__(self, other):
        return truediv(other, self.__wrapped__)

    def __rfloordiv__(self, other):
        return other // self.__wrapped__

    def __rmod__(self, other):
        return other % self.__wrapped__

    def __rdivmod__(self, other):
        return divmod(other, self.__wrapped__)

    def __rpow__(self, other, *args):
        return pow(other, self.__wrapped__, *args)

    def __rlshift__(self, other):
        return other << self.__wrapped__

    def __rrshift__(self, other):
        return other >> self.__wrapped__

    def __rand__(self, other):
        return other & self.__wrapped__

    def __rxor__(self, other):
        return other ^ self.__wrapped__

    def __ror__(self, other):
        return other | self.__wrapped__

    def __iadd__(self, other):
        self.__wrapped__ += other
        return self

    def __isub__(self, other):
        self.__wrapped__ -= other
        return self

    def __imul__(self, other):
        self.__wrapped__ *= other
        return self

    def __itruediv__(self, other):
        self.__wrapped__ = itruediv(self.__wrapped__, other)
        return self

    def __ifloordiv__(self, other):
        self.__wrapped__ //= other
        return self

    def __imod__(self, other):
        self.__wrapped__ %= other
        return self

    def __ipow__(self, other):
        self.__wrapped__ **= other
        return self

    def __ilshift__(self, other):
        self.__wrapped__ <<= other
        return self

    def __irshift__(self, other):
        self.__wrapped__ >>= other
        return self

    def __iand__(self, other):
        self.__wrapped__ &= other
        return self

    def __ixor__(self, other):
        self.__wrapped__ ^= other
        return self

    def __ior__(self, other):
        self.__wrapped__ |= other
        return self

    def __neg__(self):
        return -self.__wrapped__

    def __pos__(self):
        return +self.__wrapped__

    def __abs__(self):
        return abs(self.__wrapped__)

    def __invert__(self):
        return ~self.__wrapped__

    def __int__(self):
        return int(self.__wrapped__)

    def __float__(self):
        return float(self.__wrapped__)

    def __complex__(self):
        return complex(self.__wrapped__)

    def __oct__(self):
        return oct(self.__wrapped__)

    def __hex__(self):
        return hex(self.__wrapped__)

    def __index__(self):
        return index(self.__wrapped__)

    def __len__(self):
        return len(self.__wrapped__)

    def __contains__(self, value):
        return value in self.__wrapped__

    def __getitem__(self, key):
        return self.__wrapped__[key]

    def __setitem__(self, key, value):
        self.__wrapped__[key] = value

    def __delitem__(self, key):
        del self.__wrapped__[key]

    def __getslice__(self, i, j):
        return self.__wrapped__[i:j]

    def __setslice__(self, i, j, value):
        self.__wrapped__[i:j] = value

    def __delslice__(self, i, j):
        del self.__wrapped__[i:j]

    def __enter__(self):
        return self.__wrapped__.__enter__()

    def __exit__(self, *args, **kwargs):
        return self.__wrapped__.__exit__(*args, **kwargs)

    def __iter__(self):
        return iter(self.__wrapped__)

    def __copy__(self):
        raise NotImplementedError('object proxy must define __copy__()')

    def __deepcopy__(self, memo):
        raise NotImplementedError('object proxy must define __deepcopy__()')

    def __reduce__(self):
        raise NotImplementedError(
                'object proxy must define __reduce_ex__()')

    def __reduce_ex__(self, protocol):
        raise NotImplementedError(
                'object proxy must define __reduce_ex__()')

    def __call__(self, *args, **kwargs):
        return self.__wrapped__(*args, **kwargs)


class AwaitableProxy(ObjectProxy):
    def __await__(self):
        return self.__get_wrapped().__await__()
    
    async def __aenter__(self):
        return await self.__wrapped__.__aenter__()
    
    async def __aexit__(self, *args, **kwargs):
        return await self.__wrapped__.__aexit__(*args, **kwargs)
    
    async def __aiter__(self):
        return await self.__wrapped__.__aiter__()
    
    async def __anext__(self):
        return await self.__wrapped__.__anext__()
    
    async def __get_wrapped(self):
        return self.__wrapped__
