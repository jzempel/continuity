#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    shell
    ~~~~~

    Main continuity entry point.

    :copyright: 2012 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from continuity.cli import main
import certifi  # Import needed for pyinstaller.

if __name__ == "__main__":
    main()
