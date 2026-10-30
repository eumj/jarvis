from datetime import date

import pytest

from jarvis import models
from jarvis.cli import run

D1, D2 = date(2026, 10, 30), date(2026, 10, 31)


def test_complete_task_awards_xp_points_and_streak():
    s = models.State()
    t = models.add_task(s, "문제 풀기", D1, difficulty=2)
    r = models.complete_task(s, t.id, D1)
    assert r["xp"] == 20 + 2          # streak 1 bonus
    assert s.xp == s.points == 22 and s.streak == 1 and t.done


def test_double_completion_does_not_pay_twice():
    s = models.State()
    t = models.add_task(s, "a", D1)
    models.complete_task(s, t.id, D1)
    xp = s.xp
    with pytest.raises(ValueError):
        models.complete_task(s, t.id, D1)
    assert s.xp == xp


def test_unknown_task_id():
    with pytest.raises(KeyError):
        models.complete_task(models.State(), 99, D1)


def test_streak_continues_next_day():
    s = models.State()
    a = models.add_task(s, "a", D1)
    b = models.add_task(s, "b", D2)
    models.complete_task(s, a.id, D1)
    assert models.complete_task(s, b.id, D2)["streak"] == 2


def test_boss_task_gives_boss_xp_and_one_time_bonus():
    s = models.State()
    t = models.add_task(s, "모의고사", D1, kind="boss")
    r = models.complete_task(s, t.id, D1)
    assert r["xp"] >= 100 and r["bonus_points"] == 50
    assert s.points == r["xp"] + 50
    with pytest.raises(ValueError):
        models.complete_task(s, t.id, D1)
    assert s.points == r["xp"] + 50


def test_normal_task_has_no_bonus():
    s = models.State()
    t = models.add_task(s, "a", D1)
    assert models.complete_task(s, t.id, D1)["bonus_points"] == 0


def test_save_load_roundtrip(tmp_path):
    s = models.State()
    models.add_goal(s, "파이썬")
    t = models.add_task(s, "a", D1, goal_id=1)
    models.complete_task(s, t.id, D1)
    p = tmp_path / "state.json"
    models.save(s, p)
    assert models.load(p) == s


def test_cli_flow_and_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_DATA", str(tmp_path / "s.json"))
    assert run(["add-task", "읽기", "--difficulty", "2"], today=D1) == 0
    assert run(["done", "1"], today=D1) == 0
    assert run(["done", "1"], today=D1) == 1       # already done
    assert run(["done", "42"], today=D1) == 1      # unknown id
    assert run(["status"], today=D1) == 0
    assert "레벨 1" in capsys.readouterr().out
