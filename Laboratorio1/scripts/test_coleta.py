from unittest.mock import patch

import pytest
from coleta import (
    _build_stats_query,
    check_connection,
    fetch_top_repositories,
    get_github_token,
    run_graphql_query,
)


def _make_search_node(name="example", language="Python"):
    return {
        "name": name,
        "nameWithOwner": f"owner/{name}",
        "stargazerCount": 50000,
        "createdAt": "2010-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "primaryLanguage": {"name": language} if language else None,
    }


def _make_search_response(nodes, has_next=False, cursor=None):
    return {
        "data": {
            "search": {
                "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                "nodes": nodes,
            }
        }
    }


def _make_stats_response(count):
    data = {}
    for i in range(count):
        data[f"r{i}"] = {
            "mergedPullRequests": {"totalCount": 1000},
            "releases": {"totalCount": 50},
            "openIssues": {"totalCount": 100},
            "closedIssues": {"totalCount": 900},
        }
    return {"data": data}


def test_get_github_token_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "token-de-teste")
    assert get_github_token() == "token-de-teste"


def test_get_github_token_raises_when_missing(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        get_github_token()


@patch("coleta.requests.post")
def test_run_graphql_query_returns_data_on_success(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"data": {"viewer": {"login": "octocat"}}}

    result = run_graphql_query("query { viewer { login } }", {}, token="token-de-teste")

    assert result == {"viewer": {"login": "octocat"}}
    called_kwargs = mock_post.call_args.kwargs
    assert called_kwargs["headers"]["Authorization"] == "Bearer token-de-teste"


@patch("coleta.requests.post")
def test_run_graphql_query_raises_on_http_error(mock_post):
    mock_post.return_value.status_code = 401
    mock_post.return_value.text = "Bad credentials"

    with pytest.raises(RuntimeError):
        run_graphql_query("query { viewer { login } }", {}, token="token-invalido")


@patch("coleta.requests.post")
def test_run_graphql_query_raises_on_graphql_errors(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "errors": [{"message": "Something went wrong"}]
    }

    with pytest.raises(RuntimeError):
        run_graphql_query("query { viewer { login } }", {}, token="token-de-teste")


@patch("coleta.requests.post")
def test_check_connection_returns_viewer_login(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"data": {"viewer": {"login": "octocat"}}}

    assert check_connection(token="token-de-teste") == "octocat"


def test_build_stats_query_generates_aliases():
    query = _build_stats_query(["owner/repo-a", "owner/repo-b"])
    assert 'r0: repository(owner: "owner", name: "repo-a")' in query
    assert 'r1: repository(owner: "owner", name: "repo-b")' in query
    assert "pullRequests(states: MERGED)" in query
    assert "issues(states: OPEN)" in query
    assert "issues(states: CLOSED)" in query


@patch("coleta.requests.post")
def test_fetch_top_repositories_returns_expected_fields(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.side_effect = [
        _make_search_response([_make_search_node("react")], has_next=False),
        _make_stats_response(1),
    ]

    repos = fetch_top_repositories(count=1, token="tok")

    assert len(repos) == 1
    repo = repos[0]
    assert repo["name"] == "react"
    assert repo["nameWithOwner"] == "owner/react"
    assert repo["stargazerCount"] == 50000
    assert repo["createdAt"] == "2010-01-01T00:00:00Z"
    assert repo["updatedAt"] == "2024-01-01T00:00:00Z"
    assert repo["primaryLanguage"] == "Python"
    assert repo["mergedPullRequestsCount"] == 1000
    assert repo["releasesCount"] == 50
    assert repo["openIssuesCount"] == 100
    assert repo["closedIssuesCount"] == 900


@patch("coleta.requests.post")
def test_fetch_top_repositories_handles_null_language(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.side_effect = [
        _make_search_response([_make_search_node("dotfiles", language=None)], has_next=False),
        _make_stats_response(1),
    ]

    repos = fetch_top_repositories(count=1, token="tok")

    assert repos[0]["primaryLanguage"] is None


@patch("coleta.requests.post")
def test_fetch_top_repositories_paginates_until_count(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.side_effect = [
        _make_search_response(
            [_make_search_node(f"repo{i}") for i in range(3)],
            has_next=True,
            cursor="cursor1",
        ),
        _make_search_response(
            [_make_search_node(f"repo{i}") for i in range(3, 5)],
            has_next=False,
        ),
        _make_stats_response(5),
    ]

    repos = fetch_top_repositories(count=5, token="tok")

    assert len(repos) == 5
    assert mock_post.call_count == 3


@patch("coleta.requests.post")
def test_fetch_top_repositories_stops_at_count_before_page_end(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.side_effect = [
        _make_search_response(
            [_make_search_node(f"repo{i}") for i in range(10)], has_next=False
        ),
        _make_stats_response(3),
    ]

    repos = fetch_top_repositories(count=3, token="tok")

    assert len(repos) == 3
