from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules = cythonize("a_sync/a_sync/_flags.pyx") + cythonize("a_sync/a_sync/_kwargs.pyx")
)