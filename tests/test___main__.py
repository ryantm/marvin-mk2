from typing import Any
from typing import Dict
from typing import List
from typing import Tuple

from gidgethub import sansio

from marvin import __main__ as main


class GitHubAPIMock:
    def __init__(self) -> None:
        self.post_data: List[Tuple[str, Dict[str, Any]]] = []
        self.delete_urls: List[str] = []

    async def post(self, url: str, oauth_token: str, data: Dict[str, Any]) -> None:
        self.post_data.append((url, data))

    async def delete(self, url: str, oauth_token: str) -> None:
        self.delete_urls.append(url)


async def test_adds_needs_review_label() -> None:
    data = {
        "action": "created",
        "issue": {
            "url": "issue-url",
            "pull_request": {"url": "pr-url"},
            "user": {"id": 42, "login": "somebody"},
            "labels": [{"name": "marvin"}],
        },
        "comment": {
            "body": "/status needs_review",
            "user": {"id": 42, "login": "somebody"},
        },
    }
    event = sansio.Event(data, event="issue_comment", delivery_id="1")
    gh = GitHubAPIMock()
    await main.router.dispatch(event, gh, token="fake-token")
    assert gh.post_data == [("issue-url/labels", {"labels": ["needs_review"]})]


async def test_removes_old_status_labels_on_new_status() -> None:
    data = {
        "action": "created",
        "issue": {
            "url": "issue-url",
            "pull_request": {"url": "pr-url"},
            "user": {"id": 42, "login": "somebody"},
            "labels": [
                {"name": "marvin"},
                {"name": "needs_work"},
                {"name": "needs_merge"},
            ],
        },
        "comment": {
            "body": "/status needs_review",
            "user": {"id": 42, "login": "somebody"},
        },
    }
    event = sansio.Event(data, event="issue_comment", delivery_id="1")
    gh = GitHubAPIMock()
    await main.router.dispatch(event, gh, token="fake-token")
    assert gh.post_data == [("issue-url/labels", {"labels": ["needs_review"]})]
    assert set(gh.delete_urls) == {
        "issue-url/labels/needs_merge",
        "issue-url/labels/needs_work",
    }


async def test_responds_to_pull_request_summary_commands() -> None:
    data = {
        "action": "submitted",
        "pull_request": {
            "url": "pr-url",
            "user": {"id": 42, "login": "somebody"},
            "labels": [{"name": "marvin"}, {"name": "needs_merge"}],
        },
        "review": {
            "body": "/status needs_review",
            "state": "changes_requested",
            "user": {"id": 42, "login": "somebody"},
        },
    }
    event = sansio.Event(data, event="pull_request_review", delivery_id="1")
    gh = GitHubAPIMock()
    await main.router.dispatch(event, gh, token="fake-token")
    assert gh.post_data == [
        ("pr-url/labels", {"labels": ["needs_work"]}),
        ("pr-url/labels", {"labels": ["needs_review"]}),
    ]
    assert set(gh.delete_urls) == {
        "pr-url/labels/needs_merge",
    }