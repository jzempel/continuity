:orphan:

continuity
==========

Synopsis
--------

| *git start* [--assignedtoyou|--myissues|--mywork] [--ignore] [--force] [number|key|id]

Description
-----------

This command identifies the issue or story to start, verifies that it is
assigned to you, creates a new git branch, and marks the issue or story as
"started". Use a template to configure a prefix for new branch names.

Options
-------

-u, --assignedtoyou
    *GitHub configuration only.* Only start issues assigned to you.

-m, --myissues
    *JIRA configuration only.* Only start issues for which you are the
    assignee.

-m, --mywork
    *Pivotal configuration only.* Only start stories owned by you.

-i, --ignore
    Ignore status/state when starting the selected issue/story.

-f, --force
    Allow start from a non-integration branch, otherwise all work must start
    from the integration branch set during initialization.

number|key|id
    Start the specified GitHub issue *number*, JIRA issue *key*, or Pivotal
    Tracker story *id*. If not specified, continuity will attempt to start work
    on the next available issue/story.

See Also
--------

<`<https://github.com/jzempel/continuity/wiki/Templates>`_>
