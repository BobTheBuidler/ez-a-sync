

from typing import Callable

from mypy import errors
from mypy.nodes import ClassDef, FuncDef, Arg, Var
from mypy.plugin import Plugin
from mypy.types import get_proper_type

from a_sync.modified import ASyncFunction

property_deco_names = ['a_sync.aka.property', 'a_sync.aka.cached_property', 'async_property', 'async_cached_property']

class PropertyPlugin(Plugin):
    """A plugin to make MyPy understand async properties"""
    def get_function_hook(self, fullname: str) -> Callable:
        return self.test_function_hook

    def test_function_hook(self, node: FuncDef) -> None:
        # Check if the method is decorated with your decorator
        if hasattr(node, 'decorator_list'):
            decorators = [d.id for d in node.decorator_list]
            if any(n in decorators for n in property_deco_names):
                # Get the TypeInfo of the class to which the method belongs
                class_typeinfo = self.lookup_ancestor(node, ClassDef)

                if class_typeinfo:
                    # Check if the method name is 'call'
                    if node.name in ['call', 'init', 'add', 'sub', 'div', 'mul', 'pow', 'lt', 'gt', 'lte', 'gte']:
                        raise errors.MypyError(f'Cannot define __{node.name}__')

                    property_symbol = class_typeinfo.names.get(node.name)
                    if property_symbol and isinstance(property_symbol.node, FuncDef):
                        dunder_name = f"__{node.name}__"
                        # Create a new method with the dundermethod name, arguments, and return type based on the existing property
                        dunder_method = FuncDef(
                            dunder_name,
                            [Arg(arg_name, arg_type, None) for arg_name, arg_type in ASyncFunction[[], get_proper_type(property_symbol.node.info.type)].__call__.__annotations__.items()],
                            get_proper_type(property_symbol.node.info.type)
                        )
                        
                    # Add the dundermethod to the class
                    class_typeinfo.members[dunder_name] = Var(dunder_method.name, node.line)

    def lookup_ancestor(self, node, target_type):
        while node:
            if isinstance(node, target_type):
                return node
            node = node.parent
        return None


def plugin(_version: str):
    """Plugin for MyPy Typechecking of async properties"""
    return PropertyPlugin