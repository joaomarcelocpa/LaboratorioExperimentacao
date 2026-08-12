import pytest
from coleta import get_github_token


def test_get_github_token_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "token-de-teste")
    assert get_github_token() == "token-de-teste"


def test_get_github_token_raises_when_missing(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        get_github_token()
