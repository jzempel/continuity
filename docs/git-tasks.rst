:orphan:

continuity
==========

Synopsis
--------

| *git tasks* [--[un]check <number>]

Description
-----------

This command is executed on a branch created via **git-start(1)** and displays
tasks from the associated GitHub Issue description (formatted using GitHub
Flavored Markdown) or Pivotal Tracker story.

Options
-------

-x <number>, --check <number>
    Mark the specified task as complete.

-o <number>, --uncheck <number>
    Mark the specified task as incomplete.
