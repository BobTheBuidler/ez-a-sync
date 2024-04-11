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
from sphinx.domains.python import PyFunction
from sphinx.ext.autodoc import FunctionDocumenter

from a_sync.iter import ASyncGeneratorFunction







def autodoc_skip_member_handler(app, what, name, obj, skip, options):
    """Handler for autodoc-skip-member event."""
    if isinstance(obj, ASyncGeneratorFunction) and getattr(obj, '__wrapped__'):
        if skip:
            return False
    return None


