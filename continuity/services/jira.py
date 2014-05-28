# -*- coding: utf-8 -*-
"""
    continuity.services.jira
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Jira API.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import DataObject, IDObject, RemoteService, ServiceException
from .utils import cached_property, datetime_property
from requests import RequestException
from requests.auth import _basic_auth_str
from urlparse import urljoin


class Issue(IDObject):
    """Jira issue object.
    """

    STATUS_COMPLETE = "Complete"
    STATUS_IN_PROGRESS = "In Progress"
    STATUS_NEW = "New"

    def __str__(self):
        """Issue string representation.
        """
        return self.summary

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
    def project(self):
        """Issue project accessor.
        """
        project = self.data.get("project")

        return Project(project) if project else None

    @property
    def status(self):
        """Issue status category accessor.
        """
        return self.fields.get("status", {}).get("statusCategory", {}).get(
            "name")

    @property
    def summary(self):
        """Issue summary accessor.
        """
        return self.fields.get("summary")

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
    """Jira project object.
    """

    def __str__(self):
        """project string representation.
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


class Transition(IDObject):
    """Jira transition object.
    """

    def __str__(self):
        """Get a string representation of this transition.
        """
        return self.name

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
    def status(self):
        """Transition status category accessor.
        """
        return self.data.get("to", {}).get("statusCategory", {}).get(
            "name")


class User(DataObject):
    """Jira user object.
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
    """Base Jira exception.
    """


class JiraService(RemoteService):
    """Jira service.

    :param base: The service base URL.
    :param token: The authentication token to use.
    """

    URI = "/rest/api/2/"

    def __init__(self, base, token):
        url = urljoin(base, JiraService.URI)
        super(JiraService, self).__init__(url)
        self.token = token

    def _request(self, method, resource, **kwargs):
        """Send a Jira request.

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

    def get_issues(self, jql=None):
        """Get a list of issues.

        :param jql: Default `None`. Jira Query Language string. See
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

        :param jql: Jira Query Language string.
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
        response = self._request("get", resource)
        transitions = response.get("transitions")

        for transition in transitions:
            transition = Transition(transition)

            if status is None or transition.status == status:
                ret_val.append(transition)

        return ret_val

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

    def set_issue_transition(self, issue, transition):
        """Set the transition for the given issue.

        :param issue: The issue to update.
        :param transition: The transition to assign to the issue.
        """
        resource = "issue/{0}/transitions".format(issue.key)
        data = {"transition": transition.id}
        self._request("post", resource, data=data)
        jql = "issue = {0}".format(issue.key)

        return self.get_issue(jql)
