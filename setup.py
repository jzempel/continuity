#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    setup
    ~~~~~

    Setup the continuity distribution.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from setuptools import setup
from sys import argv
import continuity

install_requires = [
    "clint",
    "GitPython",
    "Jinja2",
    "py-getch",
    "python-dateutil < 2.0",
    "requests",
    "Sphinx"
]

if "develop" in argv:
    install_requires.append("Sphinx-PyPI-upload")
elif "test" in argv:
    install_requires.append("mock")

setup(
    name=continuity.__name__,
    version=continuity.__version__,
    url="http://github.com/jzempel/continuity",
    license=continuity.__license__,
    author=continuity.__author__,
    author_email="jzempel@gmail.com",
    description="Continuous dev flow via GitHub Issues, Pivotal Tracker, or JIRA.",  # NOQA
    long_description=__doc__,
    packages=["continuity"],
    include_package_data=True,
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "continuity = continuity.cli:main"
        ]
    },
    test_suite="continuity.tests"
)
