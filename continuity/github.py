# -*- coding: utf-8 -*-
"""
    continuity.github
    ~~~~~~~~~~~~~~~~~

    GitHub API.

    :copyright: 2012 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from json import dumps, loads
from requests import request, RequestException
import re


class GitHubException(Exception):
    """Base GitHub exception.
    """


class GitHub(object):
    """GitHub service.

    :param git: Git object instance.
    :param token: GitHub OAuth token.
    """

    PATTERN_REPOSITORY = re.compile(r"^.+:(?P<repository>\w+/\w+)\.git$", re.U)
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

        response = request(method, url, **kwargs)

        try:
            response.raise_for_status()
        except RequestException, e:
            raise GitHubException(e)

        return loads(response.content)

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

    def create_pull_request(self, title, description=None, branch=None):
        """Create a pull request.

        :param title: The title for this pull request.
        :param description: Default `None`. The optional description of this
            pull request.
        :param branch: Default `None`. The base branch the pull request is for.
        """
        data = {
            "title": title,
            "body": description,
            "head": self.git.branch.name,
            "base": branch or "master"
        }

        return self._repo_request("post", "pulls", data=data)

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
        ret_val = {}
        hooks = self._repo_request("get", "hooks")

        for hook in hooks:
            name = hook["name"]
            del hook["name"]
            ret_val[name] = hook

        return ret_val
