#!/bin/bash
#
# bash completion support for continuity.
#
# copyright 2015 by Jonathan Zempel.
# license BSD, see LICENSE for more details.

_git_finish()
{
    __gitcomp "$(__git_heads)"
}
