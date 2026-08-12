from unittest.mock import patch

import pytest
from coleta import check_connection, get_github_token, run_graphql_query


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
