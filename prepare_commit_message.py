#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    prepare_commit_message
    ~~~~~~~~~~~~~~~~~~~~~~

    Git prepare-commit-msg hook.

    :copyright: 2012 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from continuity.cli import commit

if __name__ == "__main__":
    commit()
