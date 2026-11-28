import pytest

from job_posting_agent.domain.errors import InvalidInput, Unauthenticated
from job_posting_agent.domain.models import TEAM_OWNER, ensure_user, normalize_perspective


@pytest.mark.parametrize("user", ["", TEAM_OWNER])
def test_ensure_user_rejects_empty_and_team_owner(user: str) -> None:
    with pytest.raises(Unauthenticated):
        ensure_user(user)


def test_ensure_user_accepts_email() -> None:
    assert ensure_user("a@example.com") == "a@example.com"


@pytest.mark.parametrize(
    ("name", "content"), [("", "a"), ("x" * 51, "a"), ("ok", ""), ("ok", "x" * 2001), (" ", "a")]
)
def test_perspective_length_limits(name: str, content: str) -> None:
    with pytest.raises(InvalidInput):
        normalize_perspective(name, content)


def test_perspective_is_trimmed() -> None:
    assert normalize_perspective("  名前 ", "\n内容\n") == ("名前", "内容")
