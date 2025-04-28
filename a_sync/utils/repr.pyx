from itertools import islice
from typing import Any, Iterable

from cpython.dict cimport PyDict_GET_SIZE
from cpython.list cimport PyList_GET_SIZE
from cpython.object cimport Py_TYPE, PyObject, PyObject_Repr
from cpython.tuple cimport PyTuple_GET_SIZE

cdef extern from "Python.h":
    ctypedef struct PyTypeObject:
        pass
    
        
cpdef str repr_trunc(iterable: Iterable[Any]):
    """Returns a truncated `repr` for `iterable`, limited to the first 5 items."""
    cdef PyObject *iterable_ptr = <PyObject*>iterable
    cdef PyTypeObject *itype_ptr = Py_TYPE(iterable_ptr)
    if itype_ptr == List_ptr:
        return _join_first_5_reprs_list(iterable)
    elif itype_ptr == Tuple_ptr:
        return _join_first_5_reprs_tuple(iterable)
    elif itype_ptr == Dict_ptr:
        if PyDict_GET_SIZE(iterable) <= 5:
            return "{" + ", ".join(
                f"{PyObject_Repr(<PyObject*>k)}: {repr(iterable[k])}"
                for k in iterable
            ) + "}"
        else:
            return "{" + ", ".join(
                f"{PyObject_Repr(<PyObject*>k)}: {repr(iterable[k])}"
                for k in islice(iterable, 5)
            ) + ", ...}"
    elif itype_ptr == DictKeys_ptr:
        return f"dict_keys([{_join_first_5_reprs(iterable)}])"
    elif itype_ptr == DictValues_ptr:
        return f"dict_values([{_join_first_5_reprs(iterable)}])"
    elif itype_ptr == DictItems_ptr:
        return f"dict_items([{_join_first_5_reprs(iterable)}])"
    elif itype_ptr == Set_ptr:
        return "{" + _join_first_5_reprs(iterable) + "}"
    else:
        return PyObject_Repr(iterable_ptr)


l, s, d = [], set(), {}
keys, values, items = d.keys(), d.values(), d.items()
cdef PyTypeObject *List_ptr = Py_TYPE(<PyObject*>l)
cdef PyTypeObject *Tuple_ptr = Py_TYPE(<PyObject*>())
cdef PyTypeObject *Dict_ptr = Py_TYPE(<PyObject*>d)
cdef PyTypeObject *DictKeys_ptr = Py_TYPE(<PyObject*>keys)
cdef PyTypeObject *DictValues_ptr = Py_TYPE(<PyObject*>values)
cdef PyTypeObject *DictItems_ptr = Py_TYPE(<PyObject*>items)
cdef PyTypeObject *Set_ptr = Py_TYPE(<PyObject*>s)
del l, s, d, keys, values, items


cdef inline str _join_first_5_reprs_list(list[object] lst):
    if PyList_GET_SIZE(lst) <= 5:
        return f"[{', '.join(PyObject_Repr(<PyObject*>obj) for obj in lst)}]"
    else:
        return f"[{', '.join(PyObject_Repr(<PyObject*>obj) for obj in lst[:5])}, ...]"


cdef inline str _join_first_5_reprs_tuple(tuple[object, ...] tup):
    if PyTuple_GET_SIZE(tup) <= 5:
        return f"({', '.join(PyObject_Repr(<PyObject*>obj) for obj in tup)})"
    else:
        return f"({', '.join(PyObject_Repr(<PyObject*>obj) for obj in tup[:5])}, ...)"


cdef str _join_first_5_reprs_islice(iterable: Iterable[Any]):
    if len(iterable) <= 5:
        return ", ".join(PyObject_Repr(<PyObject*>obj) for obj in iterable)
    else:
        return f"{', '.join(PyObject_Repr(<PyObject*>obj) for obj in islice(iterable, 5))}, ..."
