# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

project = 'ez-a-sync'
copyright = '2024, BobTheBuidler'
author = 'BobTheBuidler'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'a_sync.sphinx.ext',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'typing_extensions': ('https://typing-extensions.readthedocs.io/en/latest/', None),
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

autodoc_default_options = {
    'undoc-members': True,
    'private-members': True,
    'special-members': ','.join([
        '__init__',
        '__call__',
        '__getitem__',
        '__iter__',
        '__aiter__',
        '__next__',
        '__anext__',
        '_Done',
        '_AsyncExecutorMixin',
    ]),
    'inherited-members': True,
    'member-order': 'groupwise',
    # hide private methods that aren't relevant to us here
    'exclude-members': ','.join([
        '_abc_impl',
        '_fget',
        '_fset',
        '_fdel',
        '_ASyncSingletonMeta__instances',
        '_ASyncSingletonMeta__lock',
        '_is_protocol',
        '_is_runtime_protocol',
    ]),
}

autodoc_typehints = "description"
# Don't show class signature with the class' name.
autodoc_class_signature = "separated"

automodule_generate_module_stub = True

sys.path.insert(0, os.path.abspath('./a_sync'))

SKIP_MODULES = [
    "a_sync.a_sync._kwargs",
    "a_sync.a_sync.aliases",
    "a_sync.asyncio.as_completed",
    "a_sync.asyncio.create_task",
    "a_sync.asyncio.gather",
    "a_sync.asyncio.utils",
    "a_sync.utils.iterators",
]

def skip_submodules(app, what, name, obj, skip, options):
    if what == "module" and obj.__name__ in SKIP_MODULES:
        skip = True
    return skip

def setup(sphinx):
    sphinx.connect("autodoc-skip-member", skip_submodules)