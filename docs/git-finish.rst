:orphan:

continuity
==========

Synopsis
--------

| *git finish* <branchname>

Description
-----------

After your branch has been successfully tested and reviewed, it is ready to be
merged into the integration branch (or whatever branch you originated a
**git-start(1) --force** from). When you execute this command, the target
*branchname* is merged into the current branch and then deleted. Finally, the
associated issue/story is marked as "finished".

Options
-------

<branchname>
    The target issue/story branch to merge into the current branch and mark as
    "finished".
