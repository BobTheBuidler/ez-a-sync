from itertools import islice
from typing import Any, Iterable


DictKeys = type({}.keys())
DictValues = type({}.values())
DictItems = type({}.items())


def repr_trunc(iterable: Iterable[Any]) -> str:
    """Returns a truncated `repr` for `iterable`, limited to the first 5 items."""
    itype = type(iterable)
    if itype is list:
        return f"[{_join_first_5_reprs(iterable)}]"
    elif itype is tuple:
        return f"({_join_first_5_reprs(iterable)})"
    elif itype is dict:
        joined = ", ".join(map(__join_dict_item, islice(iterable.items(), 5)))
        if len(iterable) > 5:
            joined += ", ..."
        return "{" + joined + "}"
    elif itype is DictKeys:
        return f"dict_keys([{_join_first_5_reprs(iterable)}])"
    elif itype is DictValues:
        return f"dict_values([{_join_first_5_reprs(iterable)}])"
    elif itype is DictItems:
        return f"dict_items([{_join_first_5_reprs(iterable)}])"
    elif itype is set:
        return "{" + _join_first_5_reprs(iterable) + "}"
    else:
        return repr(iterable)


def _join_first_5_reprs(iterable: Iterable[Any]) -> str:
    joined = ", ".join(map(repr, islice(iterable, 5)))
    if len(iterable) > 5:
        joined += ", ..."
    return joined


__join_dict_item = lambda item: ": ".join(map(repr, item))
