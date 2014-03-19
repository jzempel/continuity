continuity
==========

Synopsis
--------

| **continuity** [--version] [--help]
| **continuity** <command> [<args>]

Description
-----------

Continuity configures a git repository with a custom set of commands that
provide high-level operations for supporting GitHub Flow via GitHub Issues
or Pivotal Tracker.

Options
-------

--version
    Print the version number of continuity.
--help
    Print a synopsis of the continuity commands.

Commands
--------

init
    Initialize a git repository for use with continuity. Other continuity
    commands are not available until a repo is initialized. The initialization
    sequence: 1) identifies the integration branch, 2) targets either GitHub
    Issues or Pivotal Tracker for project management, 3) sets configuration
    defaults, and 4) aliases continuity with a set of git commands. In
    addition, a *prepare-commit-msg* git hook is created in order to amend
    commit messages with associated story/issue information. This command may
    be re-executed to update the repo's continuity configuration. See the
    GITHUB COMMANDS or PIVOTAL COMMANDS section for initialization-specific
    commands.

    Alias: **git-continuity**

start [--assignedtoyou|--mywork] [--force] [number|id]
    Start work on a branch. This command identifies the issue or story to
    start, verifies that it is assigned to you, creates a new git branch, and
    marks the issue or story as "started".

    Alias: **git-start**

    **-u, --assignedtoyou**
        *GitHub configuration only.* Only start issues assigned to you.

    **-m, --mywork**
        *Pivotal configuration only.* Only start stories owned by you.

    **-f, --force**
        Allow start from a non-integration branch, otherwise all work must
        start from the integration branch set during initialization.

    **number|id**
        Start the specified GitHub Issue *number* or Pivotal Tracker story
        *id*. If not specified, continuity will attempt to start work on the
        next available issue/story.

review
    Open a GitHub pull request for branch review. This command is executed on
    a branch created via **start**. All outstanding commits are pushed to the
    remote branch and a pull request is created in GitHub for the issue/story.
    You may continue to commit and push branch changes based on review
    feedback.

    Alias: **git-review**

finish <branchname>
    Finish work on a branch. After your branch has been successfully tested
    and reviewed, it is ready to be merged into the integration branch (or
    whatever branch you originated a **start --force** from). When you execute
    this command, the target *branchname* is merged into the current branch
    and then deleted. Finally, the associated issue/story is marked as
    "finished".

    Alias: **git-finish**

    **<branchname>**
        The target issue/story branch to merge into the current branch and
        mark as "finished".

tasks
    List and manage issue/story tasks. This command is executed on a branch
    created via **start** and displays tasks from the associated GitHub Issue
    description (formatted using GitHub Flavored Markdown) or Pivotal Tracker
    story.

    Alias: **git-tasks**

    **-x number, --check number**
        Mark the specified task as complete.

    **-o number, --uncheck number**
        Mark the specified task as incomplete.

GitHub Commands
---------------

issue
    Display issue branch information. This command is executed on an issue
    branch created via **start**.

    Alias: **git-issue**

    **-c, --comments**
        Include issue comments.

issues
    List open issues. Output is formatted to include issue ID, title, status,
    and assignee.

    Alias: **git-issues**

    **-u, --assignedtoyou**
        Only list issues assigned to you.

Pivotal Commands
----------------

backlog
    List unstarted stories from the Pivotal Tracker backlog. Output is
    formatted to include story ID, type, points, name, and owner initials.

    Alias: **git-backlog**

    **-m, --mywork**
        Only list stories owned by you.

story
    Display story branch information. This command is executed on a story
    branch created via **start**.

    Alias: **git-story**

    **-c, --comments**
        Include story comments.
