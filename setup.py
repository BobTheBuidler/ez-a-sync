import os
from glob import glob
from pathlib import Path
from Cython.Build import cythonize
from setuptools import Extension, find_packages, setup


with open("requirements.txt", "r") as f:
    requirements = list(map(str.strip, f.read().split("\n")))[:-1]

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="ez-a-sync",
    packages=find_packages(exclude=["tests", "tests.*"]),
    use_scm_version={
        "root": ".",
        "relative_to": __file__,
        "local_scheme": "no-local-version",
        "version_scheme": "python-simplified-semver",
    },
    description="A library that makes it easy to define objects that can be used for both sync and async use cases.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="BobTheBuidler",
    author_email="bobthebuidlerdefi@gmail.com",
    url="https://github.com/BobTheBuidler/a-sync",
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: Implementation :: CPython",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
    ],
    install_requires=requirements,
    setup_requires=["setuptools_scm", "cython"],
    python_requires=">=3.8,<3.14",
    package_data={
        "a_sync": ["py.typed", "*.pxd", "**/*.pxd"],
    },
    include_package_data=True,
    ext_modules=cythonize(
        [
            Extension(
                os.path.splitext(pyx_path)[0].replace(os.path.sep, "."),
                sources=[pyx_path],
                include_dirs=["include"],
            )
            for pyx_path in glob("a_sync/**/*.pyx", recursive=True)
        ],
        compiler_directives={
            "language_level": 3,
            "embedsignature": True,
            "linetrace": True,
        },
    ),
    zip_safe=False,
)
