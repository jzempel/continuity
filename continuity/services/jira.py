# -*- coding: utf-8 -*-
"""
    continuity.services.jira
    ~~~~~~~~~~~~~~~~~~~~~~~~

    JIRA API.

    :copyright: 2015 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import DataObject, IDObject, RemoteService, ServiceException
from .utils import cached_property, datetime_property
from re import sub
from requests import RequestException
from requests.auth import _basic_auth_str
from urlparse import urljoin


class Comment(IDObject):
    """JIRA comment object.
    """

    def __str__(self):
        """Comment string representation.
        """
        return self.data.get("body")

    @property
    def author(self):
        """Comment author accessor.
        """
        author = self.data.get("author")

        return User(author) if author else None

    @datetime_property
    def created(self):
        """Comment created accessor.
        """
        return self.data.get("created")

    @datetime_property
    def updated(self):
        """Comment updated accessor.
        """
        return self.data.get("updated")


class Issue(IDObject):
    """JIRA issue object.
    """

    STATUS_COMPLETE = "done"
    STATUS_IN_PROGRESS = "indeterminate"
    STATUS_NEW = "new"
    STATUS_UNDEFINED = "undefined"

    def __str__(self):
        """Issue string representation.
        """
        return self.summary

    @property
    def _status_category(self):
        """Issue status category accessor.
        """
        return self.fields.get("status", {}).get("statusCategory", {})

    @property
    def assignee(self):
        """Issue assignee accessor.
        """
        assignee = self.fields.get("assignee")

        return User(assignee) if assignee else None

    @datetime_property
    def created(self):
        """Issue created accessor.
        """
        return self.fields.get("created")

    @property
    def creator(self):
        """Issue creator accessor.
        """
        creator = self.fields.get("creator")

        return User(creator) if creator else None

    @property
    def description(self):
        """Issue description accessor.
        """
        return self.fields.get("description")

    @property
    def fields(self):
        """Issue fields accessor.
        """
        return self.data.get("fields", {})

    @property
    def key(self):
        """Issue key accessor.
        """
        return self.data.get("key")

    @property
    def labels(self):
        """Issue labels accessor.
        """
        return self.fields.get("labels", [])

    @property
    def priority(self):
        """Issue priority accessor.
        """
        priority = self.fields.get("priority")

        return priority.get("name") if priority else None

    @property
    def project(self):
        """Issue project accessor.
        """
        project = self.data.get("project")

        return Project(project) if project else None

    @property
    def status(self):
        """Issue status key accessor.
        """
        return self._status_category.get("key")

    @property
    def status_name(self):
        """Issue status name accessor.
        """
        return self._status_category.get("name")

    @property
    def summary(self):
        """Issue summary accessor.
        """
        return self.fields.get("summary")

    @property
    def tasks(self):
        """Issue sub-tasks accessor.
        """
        tasks = self.fields.get("subtasks", [])

        return [Issue(task) for task in tasks]

    @property
    def type(self):
        """Issue type name accessor.
        """
        return self.fields.get("issuetype", {}).get("name")

    @datetime_property
    def updated(self):
        """Issue updated property.
        """
        return self.fields.get("updated")


class Project(IDObject):
    """JIRA project object.
    """

    def __str__(self):
        """Project string representation.
        """
        return "{0} ({1})".format(self.name, self.key)

    @property
    def key(self):
        """Project key accessor.
        """
        return self.data.get("key")

    @property
    def name(self):
        """Project name accessor.
        """
        return self.data.get("name")


class Resolution(IDObject):
    """JIRA resolution object.
    """

    def __str__(self):
        """Get a string representation of this resolution.
        """
        return self.name

    @property
    def description(self):
        """Resolution description accessor.
        """
        return self.data.get("description")

    @property
    def name(self):
        """Resolution name accessor.
        """
        return self.data.get("name")


class Transition(IDObject):
    """JIRA transition object.
    """

    def __str__(self):
        """Get a string representation of this transition.
        """
        return self.name

    @property
    def _status_category(self):
        """Transition status category accessor.
        """
        return self.data.get("to", {}).get("statusCategory", {})

    @property
    def description(self):
        """Transition description accessor.
        """
        return self.data.get("to", {}).get("description")

    @property
    def name(self):
        """Transition name accessor.
        """
        return self.data.get("name")

    @property
    def fields(self):
        """Transition fields accessor.
        """
        return self.data.get("fields", {})

    @property
    def resolution(self):
        """Transition resolution accessor.
        """
        return self.fields.get("resolution", {})

    @property
    def resolutions(self):
        """Transition allowed resolutions accessor.
        """
        ret_val = []
        resolutions = self.resolution.get("allowedValues", [])

        for resolution in resolutions:
            ret_val.append(Resolution(resolution))

        return ret_val

    @property
    def slug(self):
        """Transition slug accessor.
        """
        if self.name:
            ret_val = sub(r"\W+", '-', self.name.lower())
        else:
            ret_val = None

        return ret_val

    @property
    def status(self):
        """Transition status key accessor.
        """
        return self._status_category.get("key")

    @property
    def status_name(self):
        """Transition status name accessor.
        """
        return self._status_category.get("name")


class User(DataObject):
    """JIRA user object.
    """

    def __cmp__(self, other):
        """Compare user objects.

        :param other: The object to compare to.
        """
        return cmp(hash(self), hash(other))

    def __hash__(self):
        """User object hash value.
        """
        return hash(self.name)

    def __str__(self):
        """Get a string representation of this user.
        """
        return self.name

    @property
    def email(self):
        """User email accessor.
        """
        return self.data.get("emailAddress")

    @property
    def name(self):
        """User name accessor.
        """
        return self.data.get("name")


class JiraException(ServiceException):
    """Base JIRA exception.
    """


class JiraService(RemoteService):
    """JIRA service.

    :param base: The service base URL.
    :param token: The authentication token to use.
    """

    URI = "/rest/api/2/"

    def __init__(self, base, token):
        self.base = base
        url = urljoin(self.base, JiraService.URI)
        super(JiraService, self).__init__(url)
        self.token = token

    def _request(self, method, resource, **kwargs):
        """Send a JIRA request.

        :param method: The HTTP method.
        :param resource: The URI resource.
        :param kwargs: Request keyword-arguments.
        """
        headers = kwargs.get("headers", {})
        headers["Authorization"] = "Basic {0}".format(self.token)

        if method.lower() in ("post", "put"):
            headers["Content-Type"] = "application/json"

        kwargs["headers"] = headers

        try:
            ret_val = super(JiraService, self)._request(method, resource,
                    **kwargs)
        except RequestException, e:
            raise JiraException(e)

        return ret_val

    def get_comments(self, issue):
        """Get issue comments.

        :param issue: The issue to get comments for.
        """
        ret_val = []
        resource = "issue/{0}/comment".format(issue.key)
        response = self._request("get", resource)
        comments = response.get("comments")

        for comment in comments:
            ret_val.append(Comment(comment))

        return ret_val

    def get_issues(self, jql=None):
        """Get a list of issues.

        :param jql: Default `None`. JIRA Query Language string. See
            `https://confluence.atlassian.com/display/JIRA/Advanced+Searching`
        """
        ret_val = []
        params = {"jql": jql}
        response = self._request("get", "search", params=params)
        issues = response.get("issues")

        for issue in issues:
            ret_val.append(Issue(issue))

        return ret_val

    def get_issue(self, jql):
        """Get an issue identified by the given JQL.

        :param jql: JIRA Query Language string.
        """
        try:
            issues = self.get_issues(jql)

            if len(issues) == 1:
                ret_val = issues[0]
            else:
                ret_val = None
        except JiraException:
            ret_val = None

        return ret_val

    def get_issue_transitions(self, issue, status=None):
        """Get issue transitions for the given issue.

        :param key: The issue to get transitions for.
        :param status: Default `None`. A status to filter by.
        """
        ret_val = []
        resource = "issue/{0}/transitions".format(issue.key)
        params = {"expand": "transitions.fields"}
        response = self._request("get", resource, params=params)
        transitions = response.get("transitions")

        for transition in transitions:
            transition = Transition(transition)

            if status is None or transition.status == status:
                ret_val.append(transition)

        return ret_val

    def get_issue_url(self, issue):
        """Get the URL for the given issue.

        :param issue: The issue to get a URL for.
        """
        path = "browse/{0}".format(issue.key)

        return urljoin(self.base, path)

    def get_project(self, key):
        """Get a project for the given key.

        :param key: The key of the project to get.
        """
        for project in self.projects:
            if project.key == key:
                ret_val = project
                break
        else:
            ret_val = None

        return ret_val

    @staticmethod
    def get_token(user, password):
        """Get an auth token for the given user.

        :param user: The user name to get a token for.
        :param password: The user password.
        """
        token = _basic_auth_str(user, password)

        return token.split(None, 1)[-1]

    def get_user(self, name=None):
        """Get a user.

        :param name: Default `None`. Optional user name, otherwise get the
            authenticated user.
        """
        if name:
            user = self._request("get", "user", params={"username": name})
        else:
            user = self._request("get", "myself")

        return User(user)

    @cached_property
    def projects(self):
        """Get a list of projects.
        """
        ret_val = []
        projects = self._request("get", "project")

        for project in projects:
            ret_val.append(Project(project))

        return ret_val

    def set_issue_assignee(self, issue, user):
        """Set the assignee of the given issue.

        :param issue: The issue to update.
        :param user: The user to assign to the issue.
        """
        resource = "issue/{0}/assignee".format(issue.key)
        data = {"name": user.name}
        self._request("put", resource, data=data)
        jql = "issue = {0}".format(issue.key)

        return self.get_issue(jql)

    def set_issue_transition(self, issue, transition, resolution=None):
        """Set the transition for the given issue.

        :param issue: The issue to update.
        :param transition: The transition to assign to the issue.
        :param resolution: Default `None`. The transition resolution.
        """
        resource = "issue/{0}/transitions".format(issue.key)
        data = {"transition": transition.id}

        if resolution:
            data["fields"] = {"resolution": {"id": resolution.id}}

        self._request("post", resource, data=data)
        jql = "issue = {0}".format(issue.key)

        return self.get_issue(jql)
