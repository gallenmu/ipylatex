from __future__ import with_statement

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import ipylatex

classifiers = [
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 3",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: BSD License",
    "Topic :: Scientific/Engineering :: Visualization",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
    "Framework :: IPython"
]

with open("README.md", "r") as fp:
    long_description = fp.read()

setup(
    name="ipylatex",
    version=ipylatex.__version__,
    author=ipylatex.__author__,
    url="https://github.com/gallenmu/ipylatex",
    py_modules=["iplatex"],
    description="IPython magics for PyLaTeX",
    long_description=long_description,
    license="BSD",
    classifiers=classifiers
)
