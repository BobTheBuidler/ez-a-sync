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
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

autodoc_typehints = "description"
autodoc_default_options = {
    'private-members': True,
    'special-members': '__init__',
    # hide private methods that aren't relevant to us here
    'exclude-members': '_abc_impl,_fget,_fset,_fdel,_ASyncSingletonMeta__instances,_ASyncSingletonMeta__lock'
}
automodule_generate_module_stub = True

sys.path.insert(0, os.path.abspath('./a_sync'))
