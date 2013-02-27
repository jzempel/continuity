# -*- coding: utf-8 -*-
"""
    continuity.github
    ~~~~~~~~~~~~~~~~~

    GitHub API.

    :copyright: 2012 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import division
from datetime import datetime
from json import dumps, loads
from requests import request, RequestException
import re


class datetime_property(object):
    """Date/time property decorator.

    :param function: The function to decorate.
    """

    FORMAT_DATETIME = "%Y-%m-%dT%H:%M:%SZ"

    def __init__(self, function):
        self.function = function

    def __get__(self, instance, owner):
        """Attribute accessor - converts a GitHub date/time value into a Python
        datetime object.

        :param instance: The instance to get an attribute for.
        :param owner: The owner class.
        """
        try:
            value = self.function(instance)
            ret_val = datetime.strptime(value, self.FORMAT_DATETIME)
        except AttributeError:
            ret_val = None

        return ret_val


class DataObject(object):
    """GitHub data object.

    :param data: Object data dictionary.
    """

    def __init__(self, data):
        self.data = data


class IDObject(DataObject):
    """GitHub ID object.
    """

    def __cmp__(self, other):
        """Compare ID objects.

        :param other: The object to compare to.
        """
        return cmp(self.id, hash(other))

    def __hash__(self):
        """ID object hash value.
        """
        return self.id

    @property
    def id(self):
        """ID accessor.
        """
        return self.data.get("id")


class Issue(IDObject):
    """GitHub issue object.
    """

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"

    @property
    def assignee(self):
        """Issue assignee accessor.
        """
        user = self.data.get("assignee")

        return User(user) if user else None

    @datetime_property
    def created(self):
        """Issue created accessor.
        """
        return self.data.get("created_at")

    @property
    def description(self):
        """Issue description accessor.
        """
        return self.data.get("body")

    @property
    def labels(self):
        """Issue labels accessor.
        """
        ret_val = []
        labels = self.data.get("labels")

        for label in labels:
            ret_val.append(Label(label))

        return ret_val

    @property
    def milestone(self):
        """Issue milestone accessor.
        """
        milestone = self.data.get("milestone")

        return Milestone(milestone) if milestone else None

    @property
    def number(self):
        """Issue number accessor.
        """
        return self.data.get("number")

    @property
    def pull_request(self):
        """Issue pull request accessor.
        """
        pull_request = self.data.get("pull_request")

        return PullRequest(pull_request) if pull_request else None

    @property
    def state(self):
        """Issue state accessor.
        """
        return self.data.get("state")

    @property
    def title(self):
        """Issue title accessor.
        """
        return self.data.get("title")

    @datetime_property
    def updated(self):
        """Issue updated accessor.
        """
        return self.data.get("updated_at")

    @property
    def url(self):
        """Issue URL accessor.
        """
        return self.data.get("html_url")

    @property
    def user(self):
        """Issue user accessor.
        """
        user = self.data.get("user")

        return User(user)


class Label(DataObject):
    """GitHub label object.
    """

    def __cmp__(self, other):
        """Compare label objects.

        :param other: The object to compare to.
        """
        return cmp(self.name, str(other))

    def __hash__(self):
        """Label hash value.
        """
        return self.name.__hash__()

    def __str__(self):
        """Label string representation.
        """
        return self.name

    @property
    def color(self):
        """Label color accessor.
        """
        return self.data.get("color")

    @property
    def name(self):
        """Label name accessor.
        """
        return self.data.get("name")

    @property
    def url(self):
        """Label URL accessor.
        """
        return self.data.get("url")


class Milestone(IDObject):
    """GitHub milestone object.
    """

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"

    @property
    def closed_issues(self):
        """Milestone closed issues count.
        """
        return self.data.get("closed_issues")

    @property
    def completion(self):
        """Milestone completion accessor.
        """
        total_issues = self.open_issues + self.closed_issues

        return self.closed_issues / total_issues

    @datetime_property
    def created(self):
        """Milestone created accessor.
        """
        return self.data.get("created_at")

    @property
    def description(self):
        """Milestone description accessor.
        """
        return self.data.get("description")

    @datetime_property
    def due(self):
        """Milestone due accessor.
        """
        return self.data.get("due_on")

    @property
    def number(self):
        """Milestone number accessor.
        """
        return self.data.get("number")

    @property
    def open_issues(self):
        """Milestone open issue count.
        """
        return self.data.get("open_issues")

    @property
    def state(self):
        """Milestone state accessor.
        """
        return self.data.get("state")

    @property
    def title(self):
        """Milestone title accessor.
        """
        return self.data.get("title")

    @datetime_property
    def updated(self):
        """Milestone updated accessor.
        """
        return self.data.get("updated_at")

    @property
    def url(self):
        """Milestone URL accessor.
        """
        return self.data.get("html_url")

    @property
    def user(self):
        """Milestone user accessor.
        """
        user = self.data.get("creator")

        return User(user)


class PullRequest(DataObject):
    """GitHub pull request object.
    """

    @property
    def url(self):
        """Pull request URL accessor.
        """
        return self.data.get("html_url")


class User(IDObject):
    """GitHub user object.
    """

    def __str__(self):
        """Get a string representation of this User.
        """
        return self.login

    @property
    def login(self):
        """User login accessor.
        """
        return self.data.get("login")

    @property
    def url(self):
        """User URL accessor.
        """
        return self.data.get("html_url")


class GitHubException(Exception):
    """Base GitHub exception.
    """


class GitHub(object):
    """GitHub service.

    :param git: Git object instance.
    :param token: GitHub OAuth token.
    """

    expression = r"^.+github\.com[/:](?P<repository>\w+/\w+)\.git$"
    PATTERN_REPOSITORY = re.compile(expression, re.U)
    URI_TEMPLATE = "https://api.github.com/{0}"

    def __init__(self, git, token):
        if git.remote and "github.com" in git.remote.url:
            self.git = git
            self.token = token
        else:
            raise GitHubException("No github remote configured.")

    def _repo_request(self, method, resource, **kwargs):
        """Send a GitHub repo request.

        :param method: The HTTP method.
        :param resource: The repo URL resource.
        :param kwargs: Request keyword-arguments.
        """
        match = re.match(self.PATTERN_REPOSITORY, self.git.remote.url)
        repository = match.group("repository")
        path = "repos/{0}/{1}".format(repository, resource)
        headers = kwargs.get("headers", {})
        headers["Authorization"] = "token {0}".format(self.token)
        kwargs["headers"] = headers

        return GitHub._request(method, path, **kwargs)

    @staticmethod
    def _request(method, resource, **kwargs):
        """Send a GitHub request.

        :param method: The HTTP method.
        :param resource: The URI resource.
        :param kwargs: Request keyword-arguments.
        """
        url = GitHub.URI_TEMPLATE.format(resource)
        kwargs["verify"] = False

        if "data" in kwargs:
            kwargs["data"] = dumps(kwargs["data"])

        if "params" in kwargs:
            for key, value in kwargs["params"].items():
                if value is None:
                    kwargs["params"][key] = "none"

        response = request(method, url, **kwargs)

        try:
            response.raise_for_status()
        except RequestException, e:
            raise GitHubException(e)

        return loads(response.content)

    def add_labels(self, number, *names):
        """Add a labels to an issue.

        :param number: The number of the issue to update.
        :param names: The label names to add.
        """
        ret_val = []
        resource = "issues/{0}/labels".format(number)

        try:
            labels = self._repo_request("post", resource, data=names)

            for label in labels:
                ret_val.append(Label(label))
        except GitHubException:
            pass  # GitHub responds with 500 on attempt to add existing label.

        return ret_val

    def create_hook(self, name, **kwargs):
        """Create a hook.

        :param name: The name for this hook (see https://api.github.com/hooks).
        :param kwargs: Configuration keyword-arguments.
        """
        data = {
            "name": name,
            "config": kwargs,
            "active": True
        }

        return self._repo_request("post", "hooks", data=data)

    def create_pull_request(self, title_or_number, description=None,
            branch=None):
        """Create a pull request.

        :param title: The title for this pull request or issue number.
        :param description: Default `None`. The optional description of this
            pull request.
        :param branch: Default `None`. The base branch the pull request is for.
        """
        data = {
            "head": self.git.branch.name,
            "base": branch or "master"
        }

        try:
            number = int(title_or_number)
            data["issue"] = number
        except ValueError:
            title = str(title_or_number)
            data["title"] = title
            data["body"] = description

        pull_request = self._repo_request("post", "pulls", data=data)

        return PullRequest(pull_request)

    @staticmethod
    def create_token(user, password, name, url=None, scopes=["repo"]):
        """Create an OAuth token for the given user.

        :param user: The GitHub user to create a token for.
        :param password: The user password.
        :param name: The name for the token.
        :param url: Default `None`. A URL associated with the token.
        :param scopes: Default `['repo']`. A list of scopes this token is for.
        """
        data = {
            "scopes": scopes,
            "note": name,
            "note_url": url
        }
        auth = (user, password)

        try:
            response = GitHub._request("post", "authorizations", data=data,
                    auth=auth)
            ret_val = response["token"]
        except GitHubException:
            ret_val = None

        return ret_val

    def get_hooks(self):
        """Get hooks.
        """
        ret_val = {}
        hooks = self._repo_request("get", "hooks")

        for hook in hooks:
            name = hook["name"]
            del hook["name"]
            ret_val[name] = hook

        return ret_val

    def get_issue(self, number):
        """Get an issue.

        :param number: The number of the issue to get.
        """
        resource = "issues/{0}".format(number)

        try:
            issue = self._repo_request("get", resource)
            ret_val = Issue(issue)
        except GitHubException:
            ret_val = None

        return ret_val

    def get_issues(self, pull_requests=False, **parameters):
        """Get issues.

        :param pull_requests: Default `False`. Determine wheter to include
            pull requests.
        :param parameters: Parameter keyword-arguments.
        """
        ret_val = []
        parameters.setdefault("direction", "asc")
        issues = self._repo_request("get", "issues", params=parameters)

        for issue in issues:
            if pull_requests or issue["pull_request"]["html_url"] is None:
                ret_val.append(Issue(issue))

        return ret_val

    def get_milestone(self, number, **parameters):
        """Get a milestone.

        :param number: The number of the milestone to get.
        """
        resource = "milestones/{0}".format(number)

        try:
            milestone = self._repo_request("get", resource)
            ret_val = Milestone(milestone)
        except GitHubException:
            ret_val = None

        return ret_val

    def get_milestones(self, **parameters):
        """Get milestones.

        :param parameters: Parameter keyword-arguments.
        """
        ret_val = []
        milestones = self._repo_request("get", "milestones", params=parameters)

        for milestone in milestones:
            ret_val.append(Milestone(milestone))

        return ret_val

    def get_user(self, login=None):
        """Get a user.

        :param login: Default `None`. Optional user login, otherwise get the
            authenticated user.
        """
        resource = "users/{0}".format(login) if login else "user"
        headers = {"Authorization": "token {0}".format(self.token)}

        try:
            user = GitHub._request("get", resource, headers=headers)
            ret_val = User(user)
        except GitHubException:
            ret_val = None

        return ret_val

    def remove_label(self, number, name):
        """Remove a labe from an issue.

        :param number: The number of the issue to update.
        :param name: The label to add.
        """
        resource = "issues/{0}/labels/{1}".format(number, name)
        self._repo_request("delete", resource)

    def set_issue(self, number, state=None, assignee=None):
        """Set the state of the issue for the given number.

        :param number: The number of the issue to update.
        :param state: Default `None`. The updated story state: ``'open'`` or
            ``'closed'``.
        :param assignee: Default `None`. The user login of the issue assignee.
        """
        data = {}

        if state:
            data["state"] = state

        if assignee:
            data["assignee"] = assignee

        resource = "issues/{0}".format(number)
        issue = self._repo_request("patch", resource, data=data)

        return Issue(issue)
