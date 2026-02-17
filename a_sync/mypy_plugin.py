from __future__ import annotations

import os
from typing import Iterable, Optional

from mypy.nodes import (
    AssignmentStmt,
    CallExpr,
    Decorator,
    Expression,
    FuncDef,
    MemberExpr,
    NameExpr,
    OverloadedFuncDef,
    StrExpr,
)
from mypy.plugin import AttributeContext, ClassDefContext, FunctionContext, MethodContext, Plugin
from mypy.plugins.common import add_attribute_to_class
from mypy.typevars import fill_typevars
from mypy.types import CallableType, Instance, Overloaded, Parameters, Type, get_proper_type

PLUGIN_METADATA_KEY = "a_sync.mypy"

ASYNC_META_FULLNAMES = {
    "a_sync.a_sync._meta.ASyncMeta",
    "a_sync.a_sync._meta.ASyncSingletonMeta",
}

ASYNC_BASE_FULLNAMES = {
    "a_sync.a_sync.abstract.ASyncABC",
    "a_sync.a_sync.base.ASyncGenericBase",
    "a_sync.a_sync.singleton.ASyncGenericSingleton",
}

ASYNC_METHOD_DESCRIPTOR_FULLNAME = "a_sync.a_sync.method.ASyncMethodDescriptor"
ASYNC_GENERATOR_FUNCTION_FULLNAME = "a_sync.iter.ASyncGeneratorFunction"

ASYNC_FUNCTION_FULLNAMES = {
    "a_sync.a_sync.decorator.a_sync",
    "a_sync.a_sync.a_sync",
}

ASYNC_FUNCTION_TYPES = {
    "a_sync.a_sync.function.ASyncFunction",
    "a_sync.a_sync.function.ASyncFunctionSyncDefault",
    "a_sync.a_sync.function.ASyncFunctionAsyncDefault",
}

ASYNC_BOUND_METHOD_TYPES = {
    "a_sync.a_sync.method.ASyncBoundMethod",
    "a_sync.a_sync.method.ASyncBoundMethodSyncDefault",
    "a_sync.a_sync.method.ASyncBoundMethodAsyncDefault",
}

ASYNC_FUTURE_FULLNAME = "a_sync.future.ASyncFuture"
PROXY_FULLNAMES = {
    "a_sync.async_property.proxy.ObjectProxy",
    "a_sync.async_property.proxy.AwaitableProxy",
}

PROPERTY_DECORATOR_FULLNAMES = {
    "a_sync.a_sync.property.a_sync_property",
    "a_sync.a_sync.property.ASyncPropertyDescriptor",
    "a_sync.a_sync.property.ASyncPropertyDescriptorSyncDefault",
    "a_sync.a_sync.property.ASyncPropertyDescriptorAsyncDefault",
    "a_sync.a_sync.property",
    "a_sync.property",
}

PROPERTY_SYNC_DEFAULT_FULLNAMES = {
    "a_sync.a_sync.property.ASyncPropertyDescriptorSyncDefault",
}

PROPERTY_ASYNC_DEFAULT_FULLNAMES = {
    "a_sync.a_sync.property.ASyncPropertyDescriptorAsyncDefault",
}

CACHED_PROPERTY_DECORATOR_FULLNAMES = {
    "a_sync.a_sync.property.a_sync_cached_property",
    "a_sync.a_sync.property.ASyncCachedPropertyDescriptor",
    "a_sync.a_sync.property.ASyncCachedPropertyDescriptorSyncDefault",
    "a_sync.a_sync.property.ASyncCachedPropertyDescriptorAsyncDefault",
    "a_sync.a_sync.cached_property",
    "a_sync.cached_property",
}

CACHED_PROPERTY_SYNC_DEFAULT_FULLNAMES = {
    "a_sync.a_sync.property.ASyncCachedPropertyDescriptorSyncDefault",
}

CACHED_PROPERTY_ASYNC_DEFAULT_FULLNAMES = {
    "a_sync.a_sync.property.ASyncCachedPropertyDescriptorAsyncDefault",
}

PROPERTY_DESCRIPTOR_BY_DEFAULT = {
    ("property", None): "a_sync.a_sync.property.ASyncPropertyDescriptor",
    ("property", "sync"): "a_sync.a_sync.property.ASyncPropertyDescriptorSyncDefault",
    ("property", "async"): "a_sync.a_sync.property.ASyncPropertyDescriptorAsyncDefault",
    ("cached", None): "a_sync.a_sync.property.ASyncCachedPropertyDescriptor",
    ("cached", "sync"): "a_sync.a_sync.property.ASyncCachedPropertyDescriptorSyncDefault",
    ("cached", "async"): "a_sync.a_sync.property.ASyncCachedPropertyDescriptorAsyncDefault",
}

PROPERTY_DESCRIPTOR_FULLNAMES = set(PROPERTY_DESCRIPTOR_BY_DEFAULT.values())

HIDDEN_METHOD_DESCRIPTOR_FULLNAME = "a_sync.a_sync.property.HiddenMethodDescriptor"

COROUTINE_FULLNAMES = {"typing.Coroutine", "collections.abc.Coroutine"}
AWAITABLE_FULLNAMES = {"typing.Awaitable", "collections.abc.Awaitable"}
ASYNC_GENERATOR_FULLNAMES = {"typing.AsyncGenerator", "collections.abc.AsyncGenerator"}
ASYNC_ITERATOR_FULLNAMES = {"typing.AsyncIterator", "collections.abc.AsyncIterator"}

STATICMETHOD_FULLNAMES = {"builtins.staticmethod"}
CLASSMETHOD_FULLNAMES = {"builtins.classmethod"}
BUILTIN_PROPERTY_FULLNAMES = {"builtins.property", "functools.cached_property"}


def _get_fullname(expr: Expression) -> Optional[str]:
    if isinstance(expr, CallExpr):
        return _get_fullname(expr.callee)
    if isinstance(expr, (NameExpr, MemberExpr)):
        return expr.fullname
    return None


def _should_skip_attr_name(name: str) -> bool:
    return name.startswith("_") or "__" in name


def _has_static_or_classmethod(decorators: Iterable[Expression]) -> bool:
    for decorator in decorators:
        fullname = _get_fullname(decorator)
        if fullname in STATICMETHOD_FULLNAMES or fullname in CLASSMETHOD_FULLNAMES:
            return True
        if isinstance(decorator, NameExpr) and decorator.name in {"staticmethod", "classmethod"}:
            return True
    return False


def _has_builtin_property(decorators: Iterable[Expression]) -> bool:
    for decorator in decorators:
        fullname = _get_fullname(decorator)
        if fullname in BUILTIN_PROPERTY_FULLNAMES:
            return True
    return False


def _parse_default_arg(expr: CallExpr) -> Optional[str]:
    for arg, name in zip(expr.args, expr.arg_names):
        if name == "default" and isinstance(arg, StrExpr):
            if arg.value in {"sync", "async"}:
                return arg.value
            return None
    if expr.args and expr.arg_names and expr.arg_names[0] is None:
        first = expr.args[0]
        if isinstance(first, StrExpr) and first.value in {"sync", "async"}:
            return first.value
    return None


def _property_info_from_decorators(
    decorators: Iterable[Expression],
) -> Optional[tuple[str, Optional[str]]]:
    for decorator in decorators:
        default = None
        fullname = _get_fullname(decorator)
        if isinstance(decorator, CallExpr):
            default = _parse_default_arg(decorator)
            fullname = _get_fullname(decorator.callee)
        if fullname in PROPERTY_DECORATOR_FULLNAMES:
            if fullname in PROPERTY_SYNC_DEFAULT_FULLNAMES:
                default = "sync"
            elif fullname in PROPERTY_ASYNC_DEFAULT_FULLNAMES:
                default = "async"
            return ("property", default)
        if fullname in CACHED_PROPERTY_DECORATOR_FULLNAMES:
            if fullname in CACHED_PROPERTY_SYNC_DEFAULT_FULLNAMES:
                default = "sync"
            elif fullname in CACHED_PROPERTY_ASYNC_DEFAULT_FULLNAMES:
                default = "async"
            return ("cached", default)
    return None


def _unwrap_awaitable(ret_type: Type) -> Type:
    proper = get_proper_type(ret_type)
    if isinstance(proper, Instance):
        fullname = proper.type.fullname
        if fullname in COROUTINE_FULLNAMES and len(proper.args) >= 3:
            return proper.args[2]
        if fullname in AWAITABLE_FULLNAMES and proper.args:
            return proper.args[0]
    return ret_type


def _async_gen_yield_type(ret_type: Type) -> Optional[Type]:
    proper = get_proper_type(ret_type)
    if isinstance(proper, Instance):
        fullname = proper.type.fullname
        if fullname in ASYNC_GENERATOR_FULLNAMES and proper.args:
            return proper.args[0]
        if fullname in ASYNC_ITERATOR_FULLNAMES and proper.args:
            return proper.args[0]
    return None


def _parameters_from_callable(callable_type: CallableType, *, drop_first: bool) -> Parameters:
    arg_types = list(callable_type.arg_types)
    arg_kinds = list(callable_type.arg_kinds)
    arg_names = list(callable_type.arg_names)
    if drop_first and arg_types:
        arg_types = arg_types[1:]
        arg_kinds = arg_kinds[1:]
        arg_names = arg_names[1:]
    return Parameters(
        arg_types,
        arg_kinds,
        arg_names,
        variables=list(callable_type.variables),
        is_ellipsis_args=callable_type.is_ellipsis_args,
        imprecise_arg_kinds=callable_type.imprecise_arg_kinds,
    )


def _callable_from_node(node: FuncDef | Decorator | OverloadedFuncDef) -> Optional[CallableType]:
    if isinstance(node, Decorator):
        return _callable_from_node(node.func)
    if isinstance(node, OverloadedFuncDef):
        if node.impl:
            impl = node.impl
            if isinstance(impl, Decorator):
                return _callable_from_node(impl.func)
            if isinstance(impl, FuncDef):
                return _callable_from_node(impl)
        if isinstance(node.type, Overloaded) and len(node.type.items) == 1:
            return node.type.items[0]
        return None
    if isinstance(node.type, CallableType):
        return node.type
    if isinstance(node.type, Overloaded) and len(node.type.items) == 1:
        return node.type.items[0]
    return None


def _named_type_or_none(api, fullname: str, args: list[Type]) -> Optional[Instance]:
    named_type_or_none = getattr(api, "named_type_or_none", None)
    if callable(named_type_or_none):
        return named_type_or_none(fullname, args)
    return api.named_type(fullname, args)


def _class_instance_type(ctx: ClassDefContext) -> Optional[Instance]:
    inst = fill_typevars(ctx.cls.info)
    if isinstance(inst, Instance):
        return inst
    return None


def _set_attr_type(ctx: ClassDefContext, name: str, typ: Instance) -> None:
    add_attribute_to_class(ctx.api, ctx.cls, name, typ, overwrite_existing=True)
    ctx.api.add_plugin_dependency(f"{ctx.cls.info.fullname}.{name}")


def _add_hidden_method(
    ctx: ClassDefContext,
    attr_name: str,
    instance_type: Optional[Instance],
    value_type: Type,
    metadata: dict,
) -> None:
    if instance_type is None:
        return
    hidden_name = f"__{attr_name}__"
    hidden_methods = set(metadata.get("hidden_methods", []))
    if hidden_name in hidden_methods or hidden_name in ctx.cls.info.names:
        return
    empty_params = Parameters([], [], [])
    hidden_type = _named_type_or_none(
        ctx.api, HIDDEN_METHOD_DESCRIPTOR_FULLNAME, [instance_type, empty_params, value_type]
    )
    if hidden_type is None:
        return
    add_attribute_to_class(ctx.api, ctx.cls, hidden_name, hidden_type, overwrite_existing=False)
    ctx.api.add_plugin_dependency(f"{ctx.cls.info.fullname}.{hidden_name}")
    hidden_methods.add(hidden_name)
    metadata["hidden_methods"] = sorted(hidden_methods)


def _descriptor_type_for_method(
    ctx: ClassDefContext,
    callable_type: CallableType,
    *,
    drop_first: bool,
) -> Optional[Instance]:
    instance_type = _class_instance_type(ctx)
    if instance_type is None:
        return None
    params = _parameters_from_callable(callable_type, drop_first=drop_first)
    value_type = _unwrap_awaitable(callable_type.ret_type)
    return _named_type_or_none(
        ctx.api, ASYNC_METHOD_DESCRIPTOR_FULLNAME, [instance_type, params, value_type]
    )


def _descriptor_type_for_async_gen(
    ctx: ClassDefContext,
    callable_type: CallableType,
    *,
    drop_first: bool,
) -> Optional[Instance]:
    params = _parameters_from_callable(callable_type, drop_first=drop_first)
    yield_type = _async_gen_yield_type(callable_type.ret_type)
    if yield_type is None:
        return None
    return _named_type_or_none(ctx.api, ASYNC_GENERATOR_FUNCTION_FULLNAME, [params, yield_type])


def _descriptor_type_for_property(
    ctx: ClassDefContext,
    *,
    kind: str,
    default: Optional[str],
    value_type: Type,
) -> Optional[Instance]:
    instance_type = _class_instance_type(ctx)
    if instance_type is None:
        return None
    fullname = PROPERTY_DESCRIPTOR_BY_DEFAULT.get((kind, default))
    if fullname is None:
        return None
    return _named_type_or_none(ctx.api, fullname, [instance_type, value_type])


def _is_async_return_type(callable_type: CallableType) -> bool:
    proper = get_proper_type(callable_type.ret_type)
    if isinstance(proper, Instance):
        return proper.type.fullname in COROUTINE_FULLNAMES | AWAITABLE_FULLNAMES
    return False


def _value_type_from_property_instance(prop_type: Type) -> Optional[Type]:
    proper = get_proper_type(prop_type)
    if isinstance(proper, Instance) and proper.type.fullname in PROPERTY_DESCRIPTOR_FULLNAMES:
        if len(proper.args) >= 2:
            return proper.args[1]
    return None


def _env_default_mode() -> Optional[str]:
    value = os.environ.get("A_SYNC_DEFAULT_MODE")
    if value in {"sync", "async"}:
        return value
    return None


def _extract_named_arg_names(ctx: MethodContext | FunctionContext) -> set[str]:
    names: set[str] = set()
    for items in ctx.arg_names:
        for item in items:
            if item:
                names.add(item)
    return names


def _wrap_async_class(ctx: ClassDefContext) -> None:
    info = ctx.cls.info
    metadata = info.metadata.setdefault(PLUGIN_METADATA_KEY, {})
    wrapped_attrs = set(metadata.get("wrapped_attrs", []))
    needs_defer = False

    for stmt in ctx.cls.defs.body:
        if isinstance(stmt, (FuncDef, Decorator, OverloadedFuncDef)):
            name = stmt.name
            if _should_skip_attr_name(name):
                continue
            if isinstance(stmt, Decorator) and _has_static_or_classmethod(stmt.decorators):
                continue
            prop_info = None
            if isinstance(stmt, Decorator):
                prop_info = _property_info_from_decorators(stmt.decorators)
            if prop_info:
                kind, default = prop_info
                callable_type = _callable_from_node(stmt)
                if callable_type is None:
                    if not ctx.api.final_iteration:
                        needs_defer = True
                    continue
                value_type = _unwrap_awaitable(callable_type.ret_type)
                descriptor_type = _descriptor_type_for_property(
                    ctx, kind=kind, default=default, value_type=value_type
                )
                if descriptor_type is not None:
                    _set_attr_type(ctx, name, descriptor_type)
                    wrapped_attrs.add(name)
                    _add_hidden_method(ctx, name, _class_instance_type(ctx), value_type, metadata)
                continue
            if isinstance(stmt, Decorator) and _has_builtin_property(stmt.decorators):
                continue

            callable_type = _callable_from_node(stmt)
            if callable_type is None:
                if not ctx.api.final_iteration:
                    needs_defer = True
                continue

            is_async_gen = False
            func = stmt.func if isinstance(stmt, Decorator) else stmt
            if isinstance(func, FuncDef):
                is_async_gen = func.is_async_generator
            descriptor_type = None
            if is_async_gen:
                descriptor_type = _descriptor_type_for_async_gen(
                    ctx, callable_type, drop_first=True
                )
            else:
                descriptor_type = _descriptor_type_for_method(ctx, callable_type, drop_first=True)
            if descriptor_type is None:
                continue
            _set_attr_type(ctx, name, descriptor_type)
            wrapped_attrs.add(name)
            continue

        if isinstance(stmt, AssignmentStmt):
            if len(stmt.lvalues) != 1:
                continue
            lvalue = stmt.lvalues[0]
            if not isinstance(lvalue, NameExpr):
                continue
            name = lvalue.name
            if _should_skip_attr_name(name):
                continue
            if not isinstance(stmt.rvalue, CallExpr):
                continue
            prop_info = _property_info_from_decorators([stmt.rvalue])
            if not prop_info:
                continue
            kind, default = prop_info
            assigned_value_type: Type | None = None
            rvalue_type = getattr(stmt.rvalue, "type", None)
            if isinstance(rvalue_type, Type):
                assigned_value_type = _value_type_from_property_instance(rvalue_type)
            if assigned_value_type is None:
                assigned_value_type = stmt.type
            if assigned_value_type is None and isinstance(rvalue_type, Type):
                assigned_value_type = rvalue_type
            if assigned_value_type is None:
                if not ctx.api.final_iteration:
                    needs_defer = True
                continue
            value_type = _unwrap_awaitable(assigned_value_type)
            descriptor_type = _descriptor_type_for_property(
                ctx, kind=kind, default=default, value_type=value_type
            )
            if descriptor_type is None:
                continue
            _set_attr_type(ctx, name, descriptor_type)
            wrapped_attrs.add(name)
            _add_hidden_method(ctx, name, _class_instance_type(ctx), value_type, metadata)

    if needs_defer and not ctx.api.final_iteration:
        ctx.api.defer()

    metadata["wrapped_attrs"] = sorted(wrapped_attrs)


def _future_or_proxy_attribute_hook(
    ctx: AttributeContext,
    attr_name: str,
    expected_fullname: str,
) -> Type:
    proper = get_proper_type(ctx.type)
    if not isinstance(proper, Instance):
        return ctx.default_attr_type
    if proper.type.fullname != expected_fullname and not proper.type.has_base(expected_fullname):
        return ctx.default_attr_type
    if not proper.args:
        return ctx.default_attr_type
    inner = proper.args[0]
    return ctx.default_attr_type


def _a_sync_function_hook(ctx: FunctionContext) -> Type:
    default = None
    coro_arg_type: Optional[CallableType] = None

    for idx, name in enumerate(ctx.callee_arg_names):
        if name == "default" and ctx.args[idx]:
            expr = ctx.args[idx][0]
            if isinstance(expr, StrExpr) and expr.value in {"sync", "async"}:
                default = expr.value
        if name == "coro_fn" and ctx.arg_types[idx]:
            candidate = ctx.arg_types[idx][0]
            proper = get_proper_type(candidate)
            if isinstance(proper, CallableType):
                coro_arg_type = proper
            elif isinstance(proper, Overloaded) and len(proper.items) == 1:
                coro_arg_type = proper.items[0]
            elif ctx.args[idx]:
                expr = ctx.args[idx][0]
                if isinstance(expr, StrExpr):
                    default = expr.value

    if default is None:
        default = _env_default_mode()

    if coro_arg_type is None:
        if default == "sync":
            return ctx.api.named_generic_type(
                "a_sync.a_sync.function.ASyncDecoratorSyncDefault", []
            )
        if default == "async":
            return ctx.api.named_generic_type(
                "a_sync.a_sync.function.ASyncDecoratorAsyncDefault", []
            )
        return ctx.default_return_type

    params = _parameters_from_callable(coro_arg_type, drop_first=False)
    value_type = _unwrap_awaitable(coro_arg_type.ret_type)

    if default is None:
        default = "async" if _is_async_return_type(coro_arg_type) else "sync"

    if default == "sync":
        return ctx.api.named_generic_type(
            "a_sync.a_sync.function.ASyncFunctionSyncDefault", [params, value_type]
        )
    return ctx.api.named_generic_type(
        "a_sync.a_sync.function.ASyncFunctionAsyncDefault", [params, value_type]
    )


def _flag_conflict_hook(ctx: MethodContext) -> Type:
    names = _extract_named_arg_names(ctx)
    if "sync" in names and "asynchronous" in names:
        ctx.api.fail(
            "Too many flags: pass at most one of 'sync' or 'asynchronous'.", ctx.context
        )
    return ctx.default_return_type


class ASyncPlugin(Plugin):
    def get_metaclass_hook(self, fullname: str):
        if fullname in ASYNC_META_FULLNAMES:
            return _wrap_async_class
        return None

    def get_base_class_hook(self, fullname: str):
        return None

    def get_function_hook(self, fullname: str):
        if fullname in ASYNC_FUNCTION_FULLNAMES:
            return _a_sync_function_hook
        return None

    def get_method_hook(self, fullname: str):
        if fullname.endswith(".__call__"):
            for base in ASYNC_FUNCTION_TYPES | ASYNC_BOUND_METHOD_TYPES:
                if fullname == f"{base}.__call__":
                    return _flag_conflict_hook
        return None

    def get_attribute_hook(self, fullname: str):
        if fullname.startswith(f"{ASYNC_FUTURE_FULLNAME}."):
            attr = fullname.rsplit(".", 1)[1]
            return lambda ctx, attr=attr: _future_or_proxy_attribute_hook(
                ctx, attr, ASYNC_FUTURE_FULLNAME
            )
        for proxy in PROXY_FULLNAMES:
            if fullname.startswith(f"{proxy}."):
                attr = fullname.rsplit(".", 1)[1]
                return lambda ctx, attr=attr, proxy=proxy: _future_or_proxy_attribute_hook(
                    ctx, attr, proxy
                )
        return None


def plugin(version: str) -> type[Plugin]:
    return ASyncPlugin
