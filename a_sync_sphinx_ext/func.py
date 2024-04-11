"""Sphinx documentation plugin used to document ASyncFunction instances.

Introduction
============

Usage
-----

The ez-a-sync extension for Sphinx requires Sphinx 2.0 or later.

Add the extension to your :file:`docs/conf.py` configuration module:

.. code-block:: python

    extensions = (...,
                  'a_sync.contrib.sphinx')

If you'd like to change the prefix for tasks in reference documentation
then you can change the ``a_sync_function_prefix`` configuration value:

.. code-block:: python

    a_sync_function_prefix = '(function)'  # < default
    a_sync_descriptor_prefix = '(descriptor)'  # < default

With the extension installed `autodoc` will automatically find
ASyncFunction objects (e.g. when using the automodule directive)
and generate the correct (as well as add a ``(function)`` prefix),
and you can also refer to the tasks using `:task:proj.tasks.add`
syntax.

Use ``.. autotask::`` to alternatively manually document a task.
"""
from inspect import signature

from docutils import nodes
from sphinx.domains.python import PyFunction
from sphinx.ext.autodoc import FunctionDocumenter

from a_sync._descriptor import ASyncDescriptor
from a_sync.modified import ASyncFunction



class ASyncFunctionDocumenter(FunctionDocumenter):
    """Document ASyncFunction instance definitions."""

    objtype = 'function'
    #member_order = 11

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, ASyncFunction) and getattr(member, '__wrapped__')

    def format_args(self):
        wrapped = getattr(self.object, '__wrapped__', None)
        if wrapped is not None:
            sig = signature(wrapped)
            if "self" in sig.parameters or "cls" in sig.parameters:
                sig = sig.replace(parameters=list(sig.parameters.values())[1:])
            return str(sig)
        return ''

    def document_members(self, all_members=False):
        pass

    def check_module(self):
        # Normally checks if *self.object* is really defined in the module
        # given by *self.modname*. But since functions decorated with the @task
        # decorator are instances living in the celery.local, we have to check
        # the wrapped function instead.
        wrapped = getattr(self.object, '__wrapped__', None)
        if wrapped and getattr(wrapped, '__module__') == self.modname:
            return True
        return super().check_module()


class ASyncFunctionDirective(PyFunction):
    """Sphinx task directive."""

    def get_signature_prefix(self, sig):
        return [nodes.Text(self.env.config.a_sync_function_prefix)]



class ASyncDescriptorDocumenter(FunctionDocumenter):
    """Document ASyncDescriptor instance definitions."""

    objtype = 'descriptor'
    #member_order = 11

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, ASyncDescriptor) and getattr(member, '__wrapped__')

    def format_args(self):
        wrapped = getattr(self.object, '__wrapped__', None)
        if wrapped is not None:
            sig = signature(wrapped)
            if "self" in sig.parameters or "cls" in sig.parameters:
                sig = sig.replace(parameters=list(sig.parameters.values())[1:])
            return str(sig)
        return ''

    def document_members(self, all_members=False):
        pass

    def check_module(self):
        # Normally checks if *self.object* is really defined in the module
        # given by *self.modname*. But since functions decorated with the @task
        # decorator are instances living in the celery.local, we have to check
        # the wrapped function instead.
        wrapped = getattr(self.object, '__wrapped__', None)
        if wrapped and getattr(wrapped, '__module__') == self.modname:
            return True
        return super().check_module()


class ASyncDescriptorDirective(PyFunction):
    """Sphinx task directive."""

    def get_signature_prefix(self, sig):
        return [nodes.Text(self.env.config.a_sync_descriptor_directive)]


def autodoc_skip_member_handler(app, what, name, obj, skip, options):
    """Handler for autodoc-skip-member event."""
    if isinstance(obj, (ASyncFunction, ASyncDescriptor)) and getattr(obj, '__wrapped__'):
        if skip:
            return False
    return None


def setup(app):
    """Setup Sphinx extension."""
    app.setup_extension('sphinx.ext.autodoc')
    
    
    # function
    app.add_autodocumenter(ASyncFunctionDocumenter)
    app.add_directive_to_domain('py', 'a_sync_function', ASyncFunctionDirective)
    app.add_config_value('a_sync_function_prefix', '(function)', True)

    # descriptor
    app.add_autodocumenter(ASyncDescriptorDocumenter)
    app.add_directive_to_domain('py', 'a_sync_descriptor', ASyncDescriptorDirective)

    app.connect('autodoc-skip-member', autodoc_skip_member_handler)

    return {
        'parallel_read_safe': True
    }
