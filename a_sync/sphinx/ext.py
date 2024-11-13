"""Sphinx documentation plugin used to document ASyncFunction instances.

Introduction
============

Usage
-----

The ez-a-sync extension for Sphinx requires Sphinx 2.0 or later.

Add the extension to your :file:`docs/conf.py` configuration module:

.. code-block:: python

    extensions = (...,
                  'a_sync.sphinx.ext')

If you'd like to change the prefix for tasks in reference documentation
then you can change the ``a_sync_function_prefix`` configuration value:

.. code-block:: python

    a_sync_function_prefix = '(function)'  # < default
    a_sync_descriptor_prefix = '(descriptor)'  # < default
    a_sync_generator_function_prefix = '(genfunc)'  # < default

With the extension installed `autodoc` will automatically find
ASyncFunction objects (e.g. when using the automodule directive)
and generate the correct (as well as add a ``(function)`` prefix),
and you can also refer to the tasks using `:task:proj.tasks.add`
syntax.

Use ``.. autotask::`` to alternatively manually document a task.
"""

from inspect import signature

from docutils import nodes
from sphinx.domains.python import PyFunction, PyMethod
from sphinx.ext.autodoc import FunctionDocumenter, MethodDocumenter

from a_sync.a_sync._descriptor import ASyncDescriptor
from a_sync.a_sync.function import (
    ASyncFunction,
    ASyncFunctionAsyncDefault,
    ASyncFunctionSyncDefault,
)
from a_sync.iter import ASyncGeneratorFunction


class _ASyncWrapperDocumenter:
    """Base class for documenters that handle wrapped ASync functions."""

    typ: type

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        """Determine if the member can be documented by this documenter.

        Args:
            member: The member to check.
            membername: The name of the member.
            isattr: Boolean indicating if the member is an attribute.
            parent: The parent object.

        Returns:
            bool: True if the member can be documented, False otherwise.
        """
        return (
            isinstance(member, cls.typ) and getattr(member, "__wrapped__") is not None
        )

    def document_members(self, all_members=False):
        """Document members of the object.

        Args:
            all_members: Boolean indicating if all members should be documented.
        """
        pass

    def check_module(self):
        """Check if the object is defined in the expected module.

        Returns:
            bool: True if the object is defined in the expected module, False otherwise.

        Note:
            Normally checks if *self.object* is really defined in the module
            given by *self.modname*. But since functions decorated with the @task
            decorator are instances living in the celery.local, we have to check
            the wrapped function instead.
        """
        wrapped = getattr(self.object, "__wrapped__", None)
        if wrapped and getattr(wrapped, "__module__") == self.modname:
            return True
        return super().check_module()


class _ASyncFunctionDocumenter(_ASyncWrapperDocumenter, FunctionDocumenter):
    """Documenter for ASyncFunction instances."""

    def format_args(self):
        """Format the arguments of the wrapped function.

        Returns:
            str: The formatted arguments.
        """
        wrapped = getattr(self.object, "__wrapped__", None)
        if wrapped is not None:
            sig = signature(wrapped)
            if "self" in sig.parameters or "cls" in sig.parameters:
                sig = sig.replace(parameters=list(sig.parameters.values())[1:])
            return str(sig)
        return ""


class _ASyncMethodDocumenter(_ASyncWrapperDocumenter, MethodDocumenter):
    """Documenter for ASyncMethod instances."""

    def format_args(self):
        """Format the arguments of the wrapped method.

        Returns:
            str: The formatted arguments.
        """
        wrapped = getattr(self.object, "__wrapped__")
        if wrapped is not None:
            return str(signature(wrapped))
        return ""


class _ASyncDirective:
    """Base class for ASync directives."""

    prefix_env: str

    def get_signature_prefix(self, sig):
        """Get the signature prefix for the directive.

        Args:
            sig: The signature to process.

        Returns:
            list: A list of nodes representing the signature prefix.
        """
        return [nodes.Text(getattr(self.env.config, self.prefix_env))]


class _ASyncFunctionDirective(_ASyncDirective, PyFunction):
    """Directive for ASyncFunction instances."""

    pass


class _ASyncMethodDirective(_ASyncDirective, PyMethod):
    """Directive for ASyncMethod instances."""

    pass


class ASyncFunctionDocumenter(_ASyncFunctionDocumenter):
    """Document ASyncFunction instance definitions."""

    objtype = "a_sync_function"
    typ = ASyncFunction
    priority = 15
    # member_order = 11


class ASyncFunctionSyncDocumenter(_ASyncFunctionDocumenter):
    """Document ASyncFunctionSyncDefault instance definitions."""

    objtype = "a_sync_function_sync"
    typ = ASyncFunctionSyncDefault
    priority = 14
    # member_order = 11


class ASyncFunctionAsyncDocumenter(_ASyncFunctionDocumenter):
    """Document ASyncFunctionAsyncDefault instance definitions."""

    objtype = "a_sync_function_async"
    typ = ASyncFunctionAsyncDefault
    priority = 13
    # member_order = 11


class ASyncFunctionDirective(_ASyncFunctionDirective):
    """Directive for ASyncFunction instances."""

    prefix_env = "a_sync_function_prefix"


class ASyncFunctionSyncDirective(_ASyncFunctionDirective):
    """Directive for ASyncFunctionSyncDefault instances."""

    prefix_env = "a_sync_function_sync_prefix"


class ASyncFunctionAsyncDirective(_ASyncFunctionDirective):
    """Directive for ASyncFunctionAsyncDefault instances."""

    prefix_env = "a_sync_function_async_prefix"


class ASyncDescriptorDocumenter(_ASyncMethodDocumenter):
    """Document ASyncDescriptor instance definitions."""

    objtype = "a_sync_descriptor"
    typ = ASyncDescriptor
    # member_order = 11


class ASyncDescriptorDirective(_ASyncMethodDirective):
    """Directive for ASyncDescriptor instances."""

    prefix_env = "a_sync_descriptor_prefix"


class ASyncGeneratorFunctionDocumenter(_ASyncFunctionDocumenter):
    """Document ASyncGeneratorFunction instance definitions."""

    objtype = "a_sync_generator_function"
    typ = ASyncGeneratorFunction
    # member_order = 11


class ASyncGeneratorFunctionDirective(_ASyncFunctionDirective):
    """Directive for ASyncGeneratorFunction instances."""

    prefix_env = "a_sync_generator_function_prefix"


def autodoc_skip_member_handler(app, what, name, obj, skip, options):
    """Handler for autodoc-skip-member event.

    Args:
        app: The Sphinx application object.
        what: The type of the object being documented.
        name: The name of the object.
        obj: The object itself.
        skip: Boolean indicating if the member should be skipped.
        options: The options for the autodoc directive.

    Returns:
        bool: True if the member should be skipped, False otherwise.
    """
    if isinstance(
        obj, (ASyncFunction, ASyncDescriptor, ASyncGeneratorFunction)
    ) and getattr(obj, "__wrapped__"):
        if skip:
            return False
    return None


def setup(app):
    """Setup Sphinx extension.

    Args:
        app: The Sphinx application object.

    Returns:
        dict: A dictionary with metadata about the extension.
    """
    app.setup_extension("sphinx.ext.autodoc")

    # function
    app.add_autodocumenter(ASyncFunctionDocumenter)
    app.add_autodocumenter(ASyncFunctionSyncDocumenter)
    app.add_autodocumenter(ASyncFunctionAsyncDocumenter)
    app.add_directive_to_domain("py", "a_sync_function", ASyncFunctionDirective)
    app.add_directive_to_domain(
        "py", "a_sync_function_sync", ASyncFunctionSyncDirective
    )
    app.add_directive_to_domain(
        "py", "a_sync_function_async", ASyncFunctionAsyncDirective
    )
    app.add_config_value("a_sync_function_sync_prefix", "ASyncFunction (sync)", True)
    app.add_config_value("a_sync_function_async_prefix", "ASyncFunction (async)", True)
    app.add_config_value("a_sync_function_prefix", "ASyncFunction", True)

    # descriptor
    app.add_autodocumenter(ASyncDescriptorDocumenter)
    app.add_directive_to_domain("py", "a_sync_descriptor", ASyncDescriptorDirective)
    app.add_config_value("a_sync_descriptor_prefix", "ASyncDescriptor", True)

    # generator

    app.add_autodocumenter(ASyncGeneratorFunctionDocumenter)
    app.add_directive_to_domain(
        "py", "a_sync_generator_function", ASyncGeneratorFunctionDirective
    )
    app.add_config_value(
        "a_sync_generator_function_prefix", "ASyncGeneratorFunction", True
    )

    app.connect("autodoc-skip-member", autodoc_skip_member_handler)

    return {"parallel_read_safe": True}
