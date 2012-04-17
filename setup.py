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

setup(
    name="continuity",
    version="0.1",
    url="http://github.com/jzempel/continuity",
    license="BSD",
    author="Jonathan Zempel",
    author_email="jzempel@gmail.com",
    description="Continuous dev flow using Pivotal Tracker and GitHub.",
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
