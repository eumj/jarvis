from datetime import date
from types import SimpleNamespace

import pytest

from jarvis import models
from jarvis.cli import run
from jarvis.planner import PlannerError, generate_plan, parse_plan, schedule

GOOD = '[{"title": "변수", "difficulty": 1, "day": 1}, {"title": "함수", "difficulty": 2, "day": 3}]'


class FakeClient:
    """Returns the queued replies in order; counts calls."""
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(content=[SimpleNamespace(text=self.replies.pop(0))])


def test_parse_valid_and_code_fence():
    assert len(parse_plan(GOOD, 7)) == 2
    assert len(parse_plan(f"```json\n{GOOD}\n```", 7)) == 2


@pytest.mark.parametrize("bad", [
    "그냥 문장입니다",
    "[not json]",
    "[]",
    '[{"title": "a", "difficulty": 5, "day": 1}]',
    '[{"title": "a", "difficulty": 1, "day": 99}]',
    '[{"title": "", "difficulty": 1, "day": 1}]',
    '[{"difficulty": 1, "day": 1}]',
])
def test_parse_rejects_bad_replies(bad):
    with pytest.raises(PlannerError):
        parse_plan(bad, 7)


def test_schedule_maps_day_to_date():
    items = parse_plan(GOOD, 7)
    dues = [d for _, d in schedule(items, date(2026, 10, 30))]
    assert dues == [date(2026, 10, 30), date(2026, 11, 1)]


def test_retry_once_then_succeed():
    client = FakeClient("깨진 응답", GOOD)
    assert len(generate_plan("파이썬", 7, client=client)) == 2
    assert client.calls == 2


def test_gives_up_after_retry():
    client = FakeClient("깨진", "또 깨진")
    with pytest.raises(PlannerError):
        generate_plan("파이썬", 7, client=client)
    assert client.calls == 2


def test_empty_goal_and_bad_days_do_not_call_api():
    client = FakeClient()
    with pytest.raises(PlannerError):
        generate_plan("  ", 7, client=client)
    with pytest.raises(PlannerError):
        generate_plan("x", 0, client=client)
    assert client.calls == 0


def test_missing_api_key_is_reported(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir("/")   # avoid picking up a local .env
    with pytest.raises(PlannerError, match="ANTHROPIC_API_KEY"):
        generate_plan("파이썬", 7)


def test_cli_plan_creates_dated_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA", str(tmp_path / "s.json"))
    assert run(["plan", "파이썬", "--days", "7"], today=date(2026, 10, 30),
               client=FakeClient(GOOD)) == 0
    s = models.load()
    assert [t.due for t in s.tasks] == ["2026-10-30", "2026-11-01"]
    assert all(t.goal_id == s.goals[0].id for t in s.tasks)


def test_cli_plan_failure_saves_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_DATA", str(tmp_path / "s.json"))
    assert run(["plan", "파이썬"], today=date(2026, 10, 30),
               client=FakeClient("x", "y")) == 1
    assert models.load().tasks == [] and "오류" in capsys.readouterr().out
