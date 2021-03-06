from typing import Any
from typing import AsyncGenerator
from typing import Dict
from typing import List

from gidgethub.aiohttp import GitHubAPI

# List of mutually exclusive status labels
ISSUE_STATUS_LABELS = {
    "needs_reviewer",
    "awaiting_reviewer",
    "awaiting_changes",
    "needs_merger",
    "awaiting_merger",
}


async def request_review(
    pull_url: str, gh_login: str, gh: GitHubAPI, token: str
) -> None:
    """Request a review on a pull request by `gh_login`."""
    url = f"{pull_url}/requested_reviewers"
    await gh.post(url, data={"reviewers": [gh_login]}, oauth_token=token)


async def num_search_results(
    gh: GitHubAPI, token: str, query_parameters: List[str],
) -> int:
    """Search github issues and pull requests and return the number of results."""
    query = "+".join(query_parameters)
    result = await gh.getitem(
        f"https://api.github.com/search/issues?q={query}", oauth_token=token
    )
    return result["total_count"]


def search_issues(
    gh: GitHubAPI, token: str, query_parameters: List[str],
) -> AsyncGenerator[Dict[str, Any], None]:
    """Search github issues and pull requests.

    As documented here:
    https://developer.github.com/v3/search/#search-issues-and-pull-requests

    A common query string is likely "repo:NixOS/nixpkgs". Returns an async
    iterator of issues, automatically handling pagination.
    """
    query = "+".join(query_parameters)
    return gh.getiter(
        f"https://api.github.com/search/issues?q={query}", oauth_token=token
    )


async def get_installation_repositories(
    gh: GitHubAPI, token: str
) -> List[Dict[str, Any]]:
    """Get the repositories the current installation is valid for.

    As documented here:
    https://developer.github.com/v3/apps/installations/#list-repositories-accessible-to-the-app-installation

    Infers the installation from the token.
    """
    # This should be getiter, but for some reason that doesn't work (returns an
    # iterator over the items in the json dict such as "total_count") and its
    # unlikely enough that pagination is an issue h ere.
    result = await gh.getitem(
        f"https://api.github.com/installation/repositories",
        accept="application/vnd.github.machine-man-preview+json",
        oauth_token=token,
    )
    return result["repositories"]


async def set_issue_status(
    issue: Dict[str, Any], status: str, gh: GitHubAPI, token: str
) -> None:
    """Sets the status of an issue while resetting other status labels"""
    assert status in ISSUE_STATUS_LABELS

    # depending on whether the issue is actually a pull request
    issue_url = issue.get("issue_url", issue["url"])

    # Labels are mutually exclusive, so clear other labels first.
    labels = issue["labels"]
    label_names = {label["name"] for label in labels}
    # should never be more than one, but better to make it a set anyway
    status_labels = label_names.intersection(ISSUE_STATUS_LABELS)
    for label in status_labels:
        if label == status:  # Don't touch the label we're supposed to set.
            continue
        await gh.delete(issue_url + "/labels/" + label, oauth_token=token)

    if status not in status_labels:
        await gh.post(
            issue_url + "/labels", data={"labels": [status]}, oauth_token=token,
        )
