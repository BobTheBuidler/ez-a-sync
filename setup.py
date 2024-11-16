from Cython.Build import cythonize
from setuptools import find_packages, setup

with open("requirements.txt", "r") as f:
    requirements = list(map(str.strip, f.read().split("\n")))[:-1]

setup(
    name="ez-a-sync",
    packages=find_packages(),
    use_scm_version={
        "root": ".",
        "relative_to": __file__,
        "local_scheme": "no-local-version",
        "version_scheme": "python-simplified-semver",
    },
    description="A library that makes it easy to define objects that can be used for both sync and async use cases.",
    author="BobTheBuidler",
    author_email="bobthebuidlerdefi@gmail.com",
    url="https://github.com/BobTheBuidler/a-sync",
    license="MIT",
    install_requires=requirements,
    setup_requires=["setuptools_scm", "cython"],
    python_requires=">=3.8,<3.13",
    package_data={
        "a_sync": ["py.typed"],
    },
    ext_modules=cythonize(
        "a_sync/**/*.pyx",
        compiler_directives={"embedsignature": True, "linetrace": True},
    ),
    zip_safe=False,
)
