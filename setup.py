#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    setup
    ~~~~~

    Setup the continuity distribution.

    :copyright: 2012 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from setuptools import setup
import continuity

setup(
    name="continuity",
    version=continuity.__version__,
    url="http://github.com/jzempel/continuity",
    license=continuity.__license__,
    author=continuity.__author__,
    author_email="jzempel@gmail.com",
    description="Continuous dev flow through Pivotal Tracker and GitHub.",
    long_description=__doc__,
    packages=["continuity"],
    include_package_data=True,
    install_requires=[
        "clint",
        "GitPython",
            # "gitdb",
            # "async",
            # "smmap",
        "requests",
            # "certifi",
            # "chardet"
    ],
    entry_points={
        "console_scripts": [
            "continuity = continuity.cli:main"
        ]
    }
)
