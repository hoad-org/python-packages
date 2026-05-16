"""Minimal setup.py for package distribution via GitHub Pages.

This repo serves as a PEP 503 package index. Individual packages
are built separately and hosted here.
"""

from setuptools import setup

setup(
    name="hoad-python-packages-index",
    version="1.0.0",
    description="Hoad Python Packages - PEP 503 compliant package index",
    author="Hoad",
    url="https://github.com/hoad-org/python-packages",
    py_modules=[],
)
