from datetime import date

import pytest

from jarvis import models
from jarvis.cli import run
from jarvis.review import HIGH_RATE, LOW_RATE, build_report, format_report, suggest

TODAY = date(2026, 10, 30)          # Friday


def state_with(*specs):
    """specs: (due, done, difficulty, kind)"""
    s = models.State()
    for due, done, diff, kind in specs:
        t = models.add_task(s, "t", date.fromisoformat(due), diff, kind=kind)
        t.done = done
    return s


def test_rate_counts_only_tasks_due_in_window():
    s = state_with(
        ("2026-10-30", True, 1, "normal"),
        ("2026-10-29", False, 1, "normal"),
        ("2026-10-31", False, 1, "normal"),   # future: excluded
        ("2026-10-01", False, 1, "normal"),   # too old: excluded
    )
    r = build_report(s, TODAY, days=7)
    assert (r["due"], r["done"], r["rate"]) == (2, 1, 0.5)


def test_empty_state_does_not_divide_by_zero():
    r = build_report(models.State(), TODAY)
    assert r["rate"] is None and "기한이 지난 과제가 없습니다" in r["suggestion"]
    assert "없음" in format_report(r)


@pytest.mark.parametrize("rate, word", [
    (LOW_RATE - 0.01, "줄이거나"), (LOW_RATE, "유지"),
    (HIGH_RATE - 0.01, "유지"), (HIGH_RATE, "올려"),
])
def test_suggestion_thresholds(rate, word):
    assert word in suggest(rate)


def test_difficulty_breakdown():
    s = state_with(("2026-10-30", True, 1, "normal"),
                   ("2026-10-30", False, 3, "normal"))
    assert build_report(s, TODAY)["by_difficulty"] == {1: 1.0, 3: 0.0}


def test_worst_weekday_needs_repeated_misses():
    # 2026-10-23 and 2026-10-30 are both Fridays
    one = state_with(("2026-10-30", False, 1, "normal"))
    assert build_report(one, TODAY)["worst_day"] is None
    two = state_with(("2026-10-30", False, 1, "normal"),
                     ("2026-10-23", False, 1, "normal"))
    assert build_report(two, TODAY, days=8)["worst_day"] == "금"


def test_boss_clear_count_and_invalid_days():
    s = state_with(("2026-10-30", True, 3, "boss"))
    assert build_report(s, TODAY)["bosses_cleared"] == 1
    with pytest.raises(ValueError):
        build_report(s, TODAY, days=0)


def test_cli_report(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_DATA", str(tmp_path / "s.json"))
    assert run(["add-task", "읽기"], today=TODAY) == 0
    assert run(["report"], today=TODAY) == 0
    assert "달성률: 0/1 (0%)" in capsys.readouterr().out
    assert run(["report", "--days", "0"], today=TODAY) == 1
