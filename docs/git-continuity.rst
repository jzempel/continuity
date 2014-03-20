:orphan:

continuity
==========

Synopsis
--------

| *git continuity*

Description
-----------

Other continuity commands are not available until a repo is initialized. The
initialization sequence: 1) identifies the integration branch, 2) targets
either GitHub Issues or Pivotal Tracker for project management, 3) sets
configuration defaults, and 4) aliases continuity with a set of git commands.
In addition, a *prepare-commit-msg* git hook is created in order to amend
commit messages with associated story/issue information. This command may be
re-executed to update the repo's continuity configuration.
