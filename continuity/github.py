# -*- coding: utf-8 -*-
"""
    github
    ~~~~~~

    GitHub API.

    :copyright: 2012 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from json import dumps, loads
from requests import post, RequestException
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

    @staticmethod
    def create_token(user, password, name, url=None, scopes=["repo"]):
        """Create an OAuth token for the given user.

        :param user: The GitHub user to create a token for.
        :param password: The user password.
        :param name: The name for the token.
        :param url: Default `None`. A URL associated with the token.
        :param scopes: Default `['repo']`. A list of scopes this token is for.
        """
        url = GitHub.URI_TEMPLATE.format("authorizations")
        data = {
            "scopes": scopes,
            "note": name,
            "note_url": url
        }
        auth = (user, password)
        response = post(url, data=dumps(data), auth=auth, verify=False)

        try:
            response.raise_for_status()
            authorization = loads(response.content)
            ret_val = authorization["token"]
        except RequestException, e:
            ret_val = None

        return ret_val

    def create_pull_request(self, title, description=None, branch=None):
        """Create a pull request.

        :param title: The title for this pull request.
        :param description: Default `None`. The optional description of this
            pull request.
        :param branch: Default `None`. The base branch the pull request is for.
        """
        match = re.match(self.PATTERN_REPOSITORY, self.git.remote.url)
        repository = match.group("repository")
        path = "repos/{0}/pulls".format(repository)
        url = self.URI_TEMPLATE.format(path)
        data = {
            "title": title,
            "body": description,
            "head": self.git.branch.name,
            "base": branch or "master"
        }
        headers = {"Authorization": "token {0}".format(self.token)}
        response = post(url, data=dumps(data), headers=headers, verify=False)

        try:
            response.raise_for_status()
        except RequestException, e:
            raise GitHubException(e)

        return loads(response.content)
