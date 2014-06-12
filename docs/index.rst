continuity
==========

Synopsis
--------

| **continuity** [--version] [--help]
| **continuity** <command> [<args>]

Description
-----------

Continuity configures a git repository with a custom set of commands that
provide high-level operations for supporting GitHub Flow via GitHub Issues,
Pivotal Tracker, or JIRA.

Options
-------

--version
    Print the version number of continuity.
--help
    Print a synopsis of the continuity commands.

Commands
--------

init
    Initialize a git repository for use with continuity.

    Alias: **git-continuity(1)**

start
    Start work on a branch.

    Alias: **git-start(1)**

review
    Open a GitHub pull request for branch review.

    Alias: **git-review(1)**

finish
    Finish work on a branch.

    Alias: **git-finish(1)**

tasks
    List and manage branch tasks.

    Alias: **git-tasks(1)**

GitHub and JIRA Commands
------------------------

issue
    Display issue branch information.

    Alias: **git-issue(1)**

issues
    List open issues.

    Alias: **git-issues(1)**

Pivotal Commands
----------------

backlog
    List unstarted backlog stories.

    Alias: **git-backlog(1)**

story
    Display story branch information.

    Alias: **git-story(1)**
