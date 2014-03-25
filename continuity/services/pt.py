# -*- coding: utf-8 -*-
"""
    continuity.services.pt
    ~~~~~~~~~~~~~~~~~~~~~~

    Pivotal Tracker API.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import IDObject, RemoteService, ServiceException
from .utils import cached_property, datetime_property
from requests import get, RequestException
from urlparse import urljoin


class Comment(IDObject):
    """Pivotal Tracker comment object.
    """

    FIELDS = ":default,person"

    @property
    def author(self):
        """Comment author accessor.
        """
        member = self.data.get("person")

        return Member(member) if member else None

    @datetime_property
    def created(self):
        """Comment created accessor.
        """
        return self.data.get("created_at")

    @property
    def text(self):
        """Comment text accessor.
        """
        return self.data.get("text")


class Member(IDObject):
    """Pivotal Tracker member object.

    :param member: Member data.
    """

    def __init__(self, member):
        super(Member, self).__init__(member)

        if "person" in self.data:
            person = self.data["person"]
            self.data.update(person)
            del self.data["person"]

    def __str__(self):
        """Get a string representation of this Member.
        """
        return self.name

    @property
    def email(self):
        """Person email accessor.
        """
        return self.data.get("email")

    @property
    def initials(self):
        """Person initials accessor.
        """
        return self.data.get("initials")

    @property
    def name(self):
        """Person name accessor.
        """
        return self.data.get("name")

    @property
    def role(self):
        """Member role accessor.
        """
        return self.data.get("role")


class Project(IDObject):
    """Pivotal Tracker project object.
    """

    FIELDS = ":default,memberships"

    @cached_property
    def members(self):
        """Project membership accessor.
        """
        ret_val = []
        memberships = self.data.get("memberships")

        for membership in memberships:
            ret_val.append(Member(membership))

        return ret_val

    @property
    def name(self):
        """Project name accessor.
        """
        return self.data.get("name")


class Story(IDObject):
    """Pivotal Tracker story object.
    """

    FIELDS = ":default,owners,requested_by"
    STATE_UNSCHEDULED = "unscheduled"
    STATE_UNSTARTED = "unstarted"
    STATE_STARTED = "started"
    STATE_FINISHED = "finished"
    STATE_DELIVERED = "delivered"
    STATE_ACCEPTED = "accepted"
    STATE_REJECTED = "rejected"
    TYPE_BUG = "bug"
    TYPE_CHORE = "chore"
    TYPE_FEATURE = "feature"
    TYPE_RELEASE = "release"

    @datetime_property
    def created(self):
        """Story created accessor.
        """
        return self.data.get("created_at")

    @property
    def description(self):
        """Story description accessor.
        """
        return self.data.get("description")

    @property
    def estimate(self):
        """Story estimate accessor.
        """
        value = self.data.get("estimate")

        return int(value) if value else None

    @property
    def name(self):
        """Story name accessor.
        """
        return self.data.get("name")

    @property
    def owners(self):
        """Story owners accessor.
        """
        ret_val = []
        owners = self.data.get("owners", [])

        for owner in owners:
            ret_val.append(Member(owner))

        return ret_val

    @property
    def requester(self):
        """Story requester accessor.
        """
        member = self.data.get("requested_by")

        return Member(member) if member else None

    @property
    def state(self):
        """Story state accessor.
        """
        return self.data.get("current_state")

    @property
    def type(self):
        """Story type accessor.
        """
        return self.data.get("story_type")

    @datetime_property
    def updated(self):
        """Story updated accessor.
        """
        return self.data.get("updated_at")

    @property
    def url(self):
        """Story URL accessor.
        """
        return self.data.get("url")


class Iteration(IDObject):
    """Pivotal Tracker iteration object.
    """

    FIELDS = ":default,stories({0})".format(Story.FIELDS)

    @datetime_property
    def finished(self):
        """Iteration finished accessor.
        """
        return self.data.get("finish")

    @property
    def number(self):
        """Iteration number accessor.
        """
        value = self.data.get("number")

        return int(value) if value else None

    @datetime_property
    def started(self):
        """Iteration started accessor.
        """
        return self.data.get("start")

    @property
    def stories(self):
        """Iteration stories accessor.
        """
        ret_val = []
        stories = self.data.get("stories")

        for story in stories:
            story = Story(story)
            ret_val.append(story)

        return ret_val


class Task(IDObject):
    """Pivotal Tracker task object.
    """

    @datetime_property
    def created(self):
        """Task created accessor.
        """
        return self.data.get("created_at")

    @property
    def description(self):
        """Task description accessor.
        """
        return self.data.get("description")

    @property
    def is_checked(self):
        """Determine if this task is checked.
        """
        return self.data.get("complete")

    @property
    def number(self):
        """Task number accessor.
        """
        value = self.data.get("position")

        return int(value) if value else None


class PivotalTrackerException(ServiceException):
    """Base Pivotal Tracker exception.
    """


class PivotalTrackerService(RemoteService):
    """Pivotal Tracker service.

    :param token: The API token to use.
    """

    URI = "https://www.pivotaltracker.com/services/v5/"

    def __init__(self, token):
        super(PivotalTrackerService, self).__init__(PivotalTrackerService.URI)
        self.token = token

    def _request(self, method, resource, **kwargs):
        """Send a Pivotal Tracker request.

        :param method: The HTTP method.
        :param resource: The URI resource.
        :param kwargs: Request keyword-arguments.
        """
        headers = kwargs.get("headers", {})
        headers["X-TrackerToken"] = self.token

        if method.lower() in ("post", "put"):
            headers["Content-Type"] = "application/json"

        kwargs["headers"] = headers

        try:
            ret_val = super(PivotalTrackerService, self)._request(method,
                    resource, **kwargs)
        except RequestException, e:
            raise PivotalTrackerException(e)

        return ret_val

    def get_backlog(self, project, limit=None):
        """Get a list of stories in the backlog.

        :param project: The project to use.
        :param limit: Limit the number of iterations to get.
        """
        ret_val = []
        resource = "projects/{0:d}/iterations".format(project.id)
        params = {"fields": Iteration.FIELDS, "scope": "current_backlog"}

        if limit:
            params["limit"] = limit

        iterations = self._request("get", resource, params=params)

        if not iterations:
            params["scope"] = "backlog"
            iterations = self._request("get", resource, params=params)

        for iteration in iterations:
            iteration = Iteration(iteration)
            ret_val.extend(iteration.stories)

        return ret_val

    def get_comments(self, project, story):
        """Get the comments for the given story.

        :param project: The project to use.
        :param story: The story to use.
        """
        ret_val = []
        resource = "projects/{0:d}/stories/{1:d}/comments".format(project.id,
                story.id)
        params = {"fields": Comment.FIELDS}
        comments = self._request("get", resource, params=params)

        for comment in comments:
            ret_val.append(Comment(comment))

        return ret_val

    def get_project(self, id):
        """Get a project for the given ID.

        :param id: The ID of the project to get.
        """
        for project in self.projects:
            if project.id == int(id):
                ret_val = project
                break
        else:
            ret_val = None

        return ret_val

    def get_story(self, project, filter):
        """Get the next story for the given filter.

        :param project: The project to use.
        :param filter: The PT API filter. See
            `https://www.pivotaltracker.com/help/faq#howcanasearchberefined`
            for details.
        """
        resource = "projects/{0:d}/stories".format(project.id)
        params = {
            "fields": Story.FIELDS,
            "filter": "type:feature,chore,bug {0}".format(filter),
            "limit": 1
        }
        stories = self._request("get", resource, params=params)

        if len(stories) == 1:
            ret_val = Story(stories[0])
        else:
            ret_val = None

        return ret_val

    def get_tasks(self, project, story):
        """Get the tasks for the given story.

        :param project: The project to use.
        :param story: The story to use.
        """
        ret_val = []
        resource = "projects/{0:d}/stories/{1:d}/tasks".format(project.id,
                story.id)
        tasks = self._request("get", resource)

        for task in tasks:
            ret_val.append(Task(task))

        return ret_val

    @staticmethod
    def get_token(user, password):
        """Get an active token for the given user.

        :param user: The user to get a token for.
        :param password: The user password.
        """
        url = urljoin(PivotalTrackerService.URI, "me")
        auth = (user, password)
        response = get(url, auth=auth, verify=False)

        try:
            response.raise_for_status()
            data = response.json()
            ret_val = data["api_token"]
        except RequestException:
            ret_val = None

        return ret_val

    @cached_property
    def projects(self):
        """Get a list of projects.
        """
        ret_val = []
        params = {"fields": Project.FIELDS}
        projects = self._request("get", "projects", params=params)

        for project in projects:
            ret_val.append(Project(project))

        return ret_val

    def set_story(self, project, story, state, owner=None):
        """Set the state of the story for the given ID.

        :param project: The project to use.
        :param story: The story to update.
        :param state: The updated story state: ``'unscheduled'``,
            ``'unstarted'``, ``'started'``, ``'finished'``, ``'delivered'``,
            ``'accepted'``, or ``'rejected'``.
        :param owner: Default `None`. Optional story owner.
        """
        resource = "projects/{0:d}/stories/{1:d}".format(project.id, story.id)
        data = {"current_state": state, "fields": Story.FIELDS}

        if owner:
            data["owner_ids"] = [owner.id]

        story = self._request("put", resource, data=data)

        return Story(story)

    def set_task(self, project, story, task, checked):
        """Set the completion of the given task.

        :param project: The project to use.
        :param story: The story the task is a part of.
        :param task: The task to update.
        :param checked: ``True`` to check the story as completed, otherwise
            ``False``.
        """
        resource = "projects/{0:d}/stories/{1:d}/tasks/{2:d}".format(
            project.id, story.id, task.id)
        data = {"complete": checked}
        task = self._request("put", resource, data=data)

        return Task(task)
