# -*- coding: utf-8 -*-
"""
    continuity.cli.pt
    ~~~~~~~~~~~~~~~~~

    Continuity Pivotal Tracker CLI commands.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import (FinishCommand as BaseFinishCommand, GitCommand,
        ReviewCommand as BaseReviewCommand, StartCommand as BaseStartCommand,
        TasksCommand as BaseTasksCommand)
from .utils import edit, less, prompt
from clint.textui import colored, indent, puts
from continuity.services.pt import PivotalTrackerService, Story
from continuity.services.utils import cached_property
from StringIO import StringIO
from sys import exit


class PivotalTrackerCommand(GitCommand):
    """Base Pivotal Tracker command.
    """

    @cached_property
    def owner(self):
        """Owner accessor.
        """
        ret_val = None
        owner_id = int(self.get_value("pivotal", "owner-id"))

        for member in self.project.members:
            if owner_id == member.id:
                ret_val = member
                break

        return ret_val

    @cached_property
    def project(self):
        """Project accessor.
        """
        id = self.get_value("pivotal", "project-id")

        return self.pt.get_project(id)

    @cached_property
    def pt(self):
        """Pivotal Tracker accessor.
        """
        token = self.get_value("pivotal", "api-token")

        return PivotalTrackerService(token)

    @cached_property
    def story(self):
        """Current branch story accessor.
        """
        configuration = self.git.get_configuration("branch",
                self.git.branch.name)

        if configuration:
            try:
                id = configuration["story"]
                filter = "id:{0}".format(id)
                ret_val = self.pt.get_story(self.project, filter)
            except KeyError:
                ret_val = None
        else:
            ret_val = None

        if not ret_val:
            exit("fatal: Not a story branch.")

        return ret_val


class BacklogCommand(PivotalTrackerCommand):
    """List unstarted backlog stories.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    name = "backlog"

    def __init__(self, parser, namespace):
        parser.add_argument("-m", "--mywork", action="store_true",
                help="list stories owned by you")
        super(BacklogCommand, self).__init__(parser, namespace)

    def execute(self):
        """Execute this backlog command.
        """
        stories = self.pt.get_backlog(self.project)
        output = StringIO()

        for story in stories:
            if story.state in [Story.STATE_UNSCHEDULED,
                    Story.STATE_UNSTARTED] and (self.namespace.mywork is False
                            or self.owner in story.owners):
                id = colored.yellow(str(story.id))

                if story.estimate is None:
                    if story.type == Story.TYPE_FEATURE:
                        type = "{0} (?)".format(story.type.upper())
                    else:
                        type = story.type.upper()
                else:
                    type = "{0} ({1:d})".format(story.type.upper(),
                            story.estimate)

                name = story.name

                if story.owners:
                    initials = []

                    for member in self.project.members:
                        if member in story.owners:
                            initials.append(member.initials)

                    name = "{0} ({1})".format(story.name, ', '.join(initials))

                message = "{0} {1}: {2}\n".format(id, type, name)
                output.write(message)

        less(output)


class FinishCommand(BaseFinishCommand, PivotalTrackerCommand):
    """Finish a story branch.
    """

    def _merge_branch(self, branch, *args):
        """Merge a branch.

        :param branch: The name of the branch to merge.
        :param *args: Merge argument list.
        """
        try:
            self.git.get_branch(branch)
            self.story  # Cache the branch story.
        finally:
            self.git.get_branch(self.branch)

        message = "[finish #{0:d}]".format(self.story.id)
        self.git.merge_branch(branch, message, args)

    def finalize(self):
        """Finalize this finish command.
        """
        if self.story.type == Story.TYPE_CHORE:
            state = Story.STATE_ACCEPTED
        else:
            state = Story.STATE_FINISHED

        self.pt.set_story(self.project, self.story, state)
        puts("Finished story #{0:d}.".format(self.story.id))
        super(FinishCommand, self).finalize()


class ReviewCommand(BaseReviewCommand, PivotalTrackerCommand):
    """Open a GitHub pull request for story branch review.
    """

    def _create_pull_request(self, branch):
        """Create a pull request.

        :param branch: The base branch the pull request is for.
        """
        default = self.get_template("pr-title", default=self.story.name,
                story=self.story)
        title = prompt("Pull request title", default)
        puts("Pull request description (optional):")
        default = self.get_template("pr-description", default=self.story.url,
                story=self.story)
        description = edit(self.git, default, suffix=".markdown")

        if description:
            with indent(3, quote=" >"):
                puts(description)

        return self.github.create_pull_request(title, description, branch)


class StartCommand(BaseStartCommand, PivotalTrackerCommand):
    """Start a branch linked to a story.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    def __init__(self, parser, namespace):
        parser.add_argument("id", help="start the specified story", nargs='?',
                type=int)
        parser.add_argument("-m", "--mywork", action="store_true",
                help="only start stories owned by you")
        parser.add_argument("-i", "--ignore", action="store_true",
                help="ignore story state")
        super(StartCommand, self).__init__(parser, namespace)

    @property
    def error(self):
        """Error message accessor.
        """
        if self.namespace.id and self.namespace.exclusive:
            ret_val = "No estimated story #{0} found assigned to you.".format(
                self.namespace.id)

            if not self.namespace.ignore:
                state = ','.join(self.states(True))
                filter = "id:{0} owner:{1} state:{2} -estimate:-1".format(
                    self.namespace.id, self.owner, state)

                if self.pt.get_story(self.project, filter):
                    ret_val = "{0}\nUse -i to ignore the state on stories assigned to you.".\
                        format(ret_val)
                    pass
        elif self.namespace.id:
            ret_val = "No estimated story #{0} found in the backlog.".format(
                self.namespace.id)

            if not self.namespace.ignore:
                state = ','.join(self.states(True))
                filter = "id:{0} state:{1} -estimate:-1".format(
                    self.namespace.id, state)

                if self.pt.get_story(self.project, filter):
                    ret_val = "{0}\nUse -i to ignore story state.".format(
                        ret_val)
        elif self.namespace.exclusive:
            ret_val = "No estimated stories found in my work."
        else:
            ret_val = "No estimated stories found in the backlog."

        return ret_val

    def execute(self):
        """Execute this start command.
        """
        if self.story:
            puts("Story: {0}".format(self.story.name))

            if not self.story.owners:
                self.story = self.pt.set_story(self.project, self.story,
                        self.story.state, self.owner)

            # Verify that owner got the story.
            if self.owner in self.story.owners:
                branch = super(StartCommand, self).execute()
                self.git.set_configuration("branch", branch,
                        story=self.story.id)
                self.pt.set_story(self.project, self.story,
                        Story.STATE_STARTED)
            else:
                exit("Unable to update story owners.")
        else:
            exit(self.error)

    def exit(self):
        """Handle start command exit.
        """
        puts("Aborted story branch.")
        super(StartCommand, self).exit()

    @staticmethod
    def states(ignore):
        """Valid story state list accessor.

        :param ignore: Determine whether to ignore started state.
        """
        if ignore:
            ret_val = (Story.STATE_UNSTARTED, Story.STATE_STARTED,
                Story.STATE_REJECTED)
        else:
            ret_val = (Story.STATE_UNSTARTED, Story.STATE_REJECTED)

        return ret_val

    @cached_property
    def story(self):
        """Target story accessor.
        """
        story_id = self.namespace.id
        exclusive = self.namespace.exclusive
        state = ','.join(self.states(self.namespace.ignore))

        if story_id and exclusive:
            puts("Retrieving story #{0} from Pivotal Tracker for {1}...".
                format(story_id, self.owner))
            filter = "id:{0} owner:{1} state:{2} -estimate:-1".format(
                story_id, self.owner, state)
        elif story_id:
            puts("Retrieving story #{0} from Pivotal Tracker...".format(
                story_id))
            filter = "id:{0} state:{1} -estimate:-1".format(story_id, state)
        elif exclusive:
            puts("Retrieving next story from Pivotal Tracker for {0}...".
                format(self.owner))
            filter = "owner:{0} state:{1} -estimate:-1".format(self.owner,
                state)
        else:
            filter = None

        if filter:
            ret_val = self.pt.get_story(self.project, filter)
        else:
            puts("Retrieving next available story from Pivotal Tracker...")
            stories = self.pt.get_backlog(self.project)
            types = (Story.TYPE_FEATURE, Story.TYPE_BUG, Story.TYPE_CHORE)

            for story in stories:
                states = self.states(self.namespace.ignore)

                if story.type in types and story.state in states and \
                        (not story.owners or self.owner in story.owners):
                    if story.type != Story.TYPE_FEATURE or story.estimate:
                        ret_val = story
                        break
            else:
                ret_val = None

        return ret_val


class StoryCommand(PivotalTrackerCommand):
    """Display story branch information.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    name = "story"

    def __init__(self, parser, namespace):
        parser.add_argument("-c", "--comments", action="store_true",
                help="include story comments")
        super(StoryCommand, self).__init__(parser, namespace)

    def execute(self):
        """Execute the story command.
        """
        puts(self.story.name)
        puts()

        if self.story.estimate is None:
            puts(self.story.type.capitalize())
        elif self.story.estimate >= 0:
            puts("{0} Estimate: {1:d} points".format(
                self.story.type.capitalize(), self.story.estimate))
        else:
            puts("{0} Unestimated.".format(self.story.type.capitalize()))

        if self.story.description:
            puts()
            puts(colored.cyan(self.story.description))

        puts()
        puts(colored.white("Requested by {0} on {1}".format(
            self.story.requester,
            self.story.created.strftime("%d %b %Y, %I:%M%p"))))
        puts(colored.white(self.story.url))

        if self.namespace.comments:
            comments = self.pt.get_comments(self.project, self.story)

            for comment in comments:
                puts()
                puts(colored.yellow("{0} ({1})".format(comment.author,
                    comment.created)))
                puts()
                puts(comment.text)


class TasksCommand(BaseTasksCommand, PivotalTrackerCommand):
    """List and manage story tasks.
    """

    def _get_tasks(self):
        """Task list accessor.
        """
        return self.pt.get_tasks(self.project, self.story)

    def _set_task(self, task, checked):
        """Task mutator.

        :param task: The task to update.
        :param checked: ``True`` if the task is complete.
        """
        return self.pt.set_task(self.project, self.story, task, checked)

    def finalize(self):
        """Finalize this tasks command.
        """
        for task in self.tasks:
            checkmark = 'x' if task.is_checked else ' '
            message = "[{0}] {1}. {2}".format(checkmark, task.number,
                    task.description)
            puts(message)
