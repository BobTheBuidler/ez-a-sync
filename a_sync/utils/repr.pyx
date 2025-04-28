from itertools import islice
from typing import Any, Iterable

from cpython.dict cimport PyDict_Size
from cpython.list cimport PyList_GET_SIZE
from cpython.object cimport Py_TYPE, PyObject_Repr
from cpython.tuple cimport PyTuple_GET_SIZE

cdef extern from "Python.h":
    ctypedef struct PyTypeObject:
        pass


L, S, D = [], set(), {}
cdef PyTypeObject *List_ptr = Py_TYPE(L)
cdef PyTypeObject *Tuple_ptr = Py_TYPE(())
cdef PyTypeObject *Dict_ptr = Py_TYPE(D)
cdef PyTypeObject *DictKeys_ptr = Py_TYPE(D.keys())
cdef PyTypeObject *DictValues_ptr = Py_TYPE(D.values())
cdef PyTypeObject *DictItems_ptr = Py_TYPE(D.items())
cdef PyTypeObject *Set_ptr = Py_TYPE(S)
del L, S, D
    

def repr_trunc(iterable: Iterable[Any]) -> str:
    """Returns a truncated `repr` for `iterable`, limited to the first 5 items."""
    cdef PyTypeObject *itype = Py_TYPE(iterable)
    if itype == List_ptr:
        return _join_first_5_reprs_list(iterable)
    elif itype == Tuple_ptr:
        return _join_first_5_reprs_tuple(iterable)
    elif itype == Dict_ptr:
        if PyDict_Size(iterable) <= 5:
            return "{" + ", ".join(
                f"{PyObject_Repr(k)}: {repr(iterable[k])}"
                for k in iterable
            ) + "}"
        else:
            return "{" + ", ".join(
                f"{PyObject_Repr(k)}: {repr(iterable[k])}"
                for k in islice(iterable, 5)
            ) + ", ...}"
    elif itype == DictKeys_ptr:
        return f"dict_keys([{_join_first_5_reprs_generic(iterable)}])"
    elif itype == DictValues_ptr:
        return f"dict_values([{_join_first_5_reprs_generic(iterable)}])"
    elif itype == DictItems_ptr:
        return f"dict_items([{_join_first_5_reprs_generic(iterable)}])"
    elif itype == Set_ptr:
        return "{" + _join_first_5_reprs_generic(iterable) + "}"
    else:
        return PyObject_Repr(iterable)


cdef inline str _join_first_5_reprs_list(list[object] lst):
    if PyList_GET_SIZE(lst) <= 5:
        return f"[{', '.join(PyObject_Repr(obj) for obj in lst)}]"
    else:
        return f"[{', '.join(PyObject_Repr(obj) for obj in lst[:5])}, ...]"


cdef inline str _join_first_5_reprs_tuple(tuple[object, ...] tup):
    if PyTuple_GET_SIZE(tup) <= 5:
        return f"({', '.join(PyObject_Repr(obj) for obj in tup)})"
    else:
        return f"({', '.join(PyObject_Repr(obj) for obj in tup[:5])}, ...)"


cdef str _join_first_5_reprs_generic(iterable: Iterable[Any]):
    if len(iterable) <= 5:
        return ", ".join(PyObject_Repr(obj) for obj in iterable)
    else:
        return f"{', '.join(PyObject_Repr(obj) for obj in islice(iterable, 5))}, ..."
