from datetime import date

import pytest

from jarvis.rewards import (BOSS_XP, level_for_xp, task_xp, update_streak,
                            xp_for_level)


def test_task_xp_scales_with_difficulty():
    assert task_xp(1) == 10
    assert task_xp(3) == 30


def test_task_xp_streak_bonus_is_capped():
    assert task_xp(2, streak=3) == 20 + 6
    assert task_xp(2, streak=100) == 20 + 14


def test_boss_xp():
    assert task_xp(1, boss=True) == BOSS_XP


def test_invalid_difficulty():
    with pytest.raises(ValueError):
        task_xp(0)


def test_level_boundaries():
    assert level_for_xp(0) == 1
    assert level_for_xp(xp_for_level(2) - 1) == 1
    assert level_for_xp(xp_for_level(2)) == 2
    assert level_for_xp(xp_for_level(5)) == 5


def test_streak_first_completion():
    assert update_streak(None, 0, date(2026, 10, 30)) == 1


def test_streak_same_day_unchanged():
    assert update_streak(date(2026, 10, 30), 4, date(2026, 10, 30)) == 4


def test_streak_next_day_increments():
    assert update_streak(date(2026, 10, 30), 4, date(2026, 10, 31)) == 5


def test_streak_across_month_and_year_boundary():
    assert update_streak(date(2026, 10, 31), 2, date(2026, 11, 1)) == 3
    assert update_streak(date(2026, 12, 31), 2, date(2027, 1, 1)) == 3


def test_streak_resets_after_gap():
    assert update_streak(date(2026, 10, 28), 9, date(2026, 10, 30)) == 1


def test_streak_rejects_past_date():
    with pytest.raises(ValueError):
        update_streak(date(2026, 10, 30), 1, date(2026, 10, 29))
