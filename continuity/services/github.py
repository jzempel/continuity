# -*- coding: utf-8 -*-
"""
    continuity.services.github
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    GitHub API.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import division
from .commons import DataObject, IDObject, RemoteService, ServiceException
from .utils import datetime_property
from json import dumps
from requests import codes, get, post, RequestException
from urlparse import urljoin
import re


class Comment(IDObject):
    """GitHub comment object.
    """

    def __str__(self):
        """Comment string representation.
        """
        return self.data.get("body")

    @datetime_property
    def created(self):
        """Comment created accessor.
        """
        return self.data.get("created_at")

    @datetime_property
    def updated(self):
        """Comment updated accessor.
        """
        return self.data.get("updated_at")

    @property
    def url(self):
        """Comment URL accessor.
        """
        return self.data.get("html_url")

    @property
    def user(self):
        """Comment user accessor.
        """
        user = self.data.get("user")

        return User(user)


class Issue(IDObject):
    """GitHub issue object.
    """

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"

    def __str__(self):
        """Issue string representation.
        """
        return self.title

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

    def __str__(self):
        """Milestone string representation.
        """
        return self.title

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


class Task(DataObject):
    """GitHub task object.
    """

    @property
    def description(self):
        """Task description accessor.
        """
        ret_val = self.data.get("description")

        if ret_val:
            ret_val = ret_val.strip()

        return ret_val

    @property
    def is_checked(self):
        """Determine if this task is checked.
        """
        value = self.data.get("checked")

        return value == 'x'

    @property
    def number(self):
        """Task number accessor.
        """
        return self.data.get("number")


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


class GitHubException(ServiceException):
    """Base GitHub exception.
    """


class GitHubRequestException(GitHubException):
    """GitHub request exception.

    :param *args: Argument list.
    :param **kwargs: Keyword arguments.
    """

    def __init__(self, *args, **kwargs):
        super(GitHubRequestException, self).__init__(*args, **kwargs)

        if self.args:
            error = self.args[0]

            if isinstance(error, RequestException):
                if hasattr(error, "response"):
                    self.response = error.response

                    if self.response is not None:
                        self.json = self.response.json()
                    else:
                        self.json = {}


class GitHubService(RemoteService):
    """GitHub service.

    :param git: Git service instance.
    :param token: GitHub OAuth token.
    """

    expression = r"^.+github\.com[/:](?P<repository>\w+/[\w\.]+)\.git$"
    PATTERN_REPOSITORY = re.compile(expression, re.U)
    expression = r"^([-*+]|\d+\.)\s+\[(?P<checked>[ x])\]\s+(?P<description>\S.*)$"  # NOQA
    PATTERN_TASK = re.compile(expression, re.M | re.U)
    URI = "https://api.github.com"
    VERSION = "application/vnd.github.v3+json"

    def __init__(self, git, token):
        super(GitHubService, self).__init__(GitHubService.URI)

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

        return self._request(method, path, **kwargs)

    def _request(self, method, resource, **kwargs):
        """Send a GitHub request.

        :param method: The HTTP method.
        :param resource: The URI resource.
        :param kwargs: Request keyword-arguments.
        """
        headers = kwargs.get("headers", {})
        headers["Accept"] = GitHubService.VERSION
        kwargs["headers"] = headers

        if "params" in kwargs:
            for key, value in kwargs["params"].items():
                if value is None:
                    kwargs["params"][key] = "none"

        try:
            ret_val = super(GitHubService, self)._request(method, resource,
                    **kwargs)
        except RequestException, e:
            raise GitHubRequestException(e)

        return ret_val

    def add_labels(self, issue, *names):
        """Add a labels to an issue.

        :param issue: The issue to add labels to.
        :param names: The label names to add.
        """
        ret_val = []
        resource = "issues/{0}/labels".format(issue.number)

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
    def create_repository(token, name, owner, entity="user"):
        """Create a new repository.

        :param name: The name of the repository to create.
        :param owner: The name of the repository owner.
        :param entity: Default ``'user'``. Specify ``'orgs/:org'`` if this is
            for an organization.
        """
        data = dumps({"name": name})
        headers = {
            "Accept": GitHubService.VERSION,
            "Authorization": "token {0}".format(token)
        }
        resource = "{0}/repos".format(entity)
        url = urljoin(GitHubService.URI, resource)
        response = post(url, data=data, headers=headers, verify=False)

        if response.status_code == codes.unprocessable:  # already exists.
            resource = "/repos/{0}/{1}".format(owner, name)
            url = urljoin(GitHubService.URI, resource)
            response = get(url, headers=headers, verify=False)
        else:
            response.raise_for_status()

        return response.json()

    @staticmethod
    def create_token(user, password, name, code=None, url=None,
            scopes=["repo"]):
        """Create an OAuth token for the given user.

        :param user: The GitHub user to create a token for.
        :param password: The user password.
        :param name: The name for the token.
        :param code: Default `None`. Two-factor authentication code.
        :param url: Default `None`. A URL associated with the token.
        :param scopes: Default `['repo']`. A list of scopes this token is for.
        """
        ret_val = None
        auth = (user, password)
        data = dumps({
            "scopes": scopes,
            "note": name,
            "note_url": url
        })
        headers = {"Accept": GitHubService.VERSION}

        if code:
            headers["X-GitHub-OTP"] = code

        url = urljoin(GitHubService.URI, "authorizations")
        response = post(url, auth=auth, data=data, headers=headers,
                verify=False)

        if response.status_code == codes.unprocessable:  # already exists.
            response = get(url, auth=auth, headers=headers, verify=False)
            authorizations = response.json()

            for authorization in authorizations:
                if authorization.get("note") == name:
                    ret_val = authorization["token"]
                    break
        elif response.status_code == codes.unauthorized and code is None and \
                "required" in response.headers.get("X-GitHub-OTP", ''):
            try:
                response.raise_for_status()
            except RequestException, e:
                raise GitHubRequestException(e)
        else:
            authorization = response.json()
            ret_val = authorization.get("token")

        return ret_val

    def get_comments(self, issue):
        """Get issue comments.

        :param issue: The issue to get comments for.
        """
        ret_val = []
        resource = "issues/{0}/comments".format(issue.number)
        comments = self._repo_request("get", resource)

        for comment in comments:
            ret_val.append(Comment(comment))

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

        :param pull_requests: Default `False`. Determine whether to include
            pull requests.
        :param parameters: Parameter keyword-arguments.
        """
        ret_val = []
        parameters.setdefault("direction", "asc")
        issues = self._repo_request("get", "issues", params=parameters)

        for issue in issues:
            if pull_requests or issue.get("pull_request") is None:
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

    @staticmethod
    def get_tasks(issue):
        """Get the tasks for the given issue.

        :param issue: The issue to use.
        """
        ret_val = []

        if issue.description:
            for index, match in enumerate(
                    GitHubService.PATTERN_TASK.finditer(issue.description)):
                data = match.groupdict()
                data["number"] = index + 1
                task = Task(data)
                ret_val.append(task)

        return ret_val

    def get_user(self, login=None):
        """Get a user.

        :param login: Default `None`. Optional user login, otherwise get the
            authenticated user.
        """
        resource = "users/{0}".format(login) if login else "user"
        headers = {"Authorization": "token {0}".format(self.token)}

        try:
            user = self._request("get", resource, headers=headers)
            ret_val = User(user)
        except GitHubException:
            ret_val = None

        return ret_val

    def remove_branch(self, name):
        """Remove a branch.

        :param name: The name of the branch to remove.
        """
        resource = "git/refs/heads/{0}".format(name)
        self._repo_request("delete", resource)

    def remove_hook(self, name):
        """Remove a hook.

        :param name: The name of the hook to remove.
        """
        hooks = self.get_hooks()

        if name in hooks:
            resource = "hooks/{0}".format(hooks[name].get("id"))
            self._repo_request("delete", resource)

    def remove_label(self, issue, name):
        """Remove a label from an issue.

        :param issue: The issue to add a label to.
        :param name: The label to add.
        """
        resource = "issues/{0}/labels/{1}".format(issue.number, name)
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

    def set_task(self, issue, task, checked):
        """Set the completion of the given task.

        :param story: The issue the task is a part of.
        :param task: The task to update.
        :param checked: ``True`` to check the story as completed, otherwise
            ``False``.
        """
        if issue.description:
            count = [1]

            def replace(match):
                ret_val = match.group(0)

                if count[0] == task.number:
                    old = "[ ]" if checked else "[x]"
                    new = "[x]" if checked else "[ ]"
                    ret_val = ret_val.replace(old, new, 1)

                count[0] += 1

                return ret_val

            description = self.PATTERN_TASK.sub(replace, issue.description)
            data = {"body": description}
            resource = "issues/{0}".format(issue.number)
            self._repo_request("patch", resource, data=data)
            task.data["checked"] = 'x' if checked else ' '

        return task
