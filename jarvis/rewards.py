"""Reward rules: XP, levels, streaks. Pure functions, no I/O."""
from datetime import date

XP_PER_DIFFICULTY = 10      # task XP = difficulty (1-3) * this
BOSS_XP = 100
STREAK_BONUS_PER_DAY = 2    # extra XP per streak day
STREAK_BONUS_CAP_DAYS = 7


def task_xp(difficulty: int, streak: int = 0, boss: bool = False) -> int:
    """XP for completing one task, including the streak bonus."""
    if boss:
        base = BOSS_XP
    else:
        if difficulty not in (1, 2, 3):
            raise ValueError("difficulty must be 1, 2 or 3")
        base = difficulty * XP_PER_DIFFICULTY
    if streak < 0:
        raise ValueError("streak must be >= 0")
    return base + min(streak, STREAK_BONUS_CAP_DAYS) * STREAK_BONUS_PER_DAY


def xp_for_level(level: int) -> int:
    """Total XP needed to reach `level` (level 1 needs 0)."""
    if level < 1:
        raise ValueError("level must be >= 1")
    return 50 * level * (level - 1)


def level_for_xp(xp: int) -> int:
    if xp < 0:
        raise ValueError("xp must be >= 0")
    level = 1
    while xp >= xp_for_level(level + 1):
        level += 1
    return level


def update_streak(last_done: date | None, streak: int, today: date) -> int:
    """New streak after completing a task on `today`.

    Same day: unchanged. Next day: +1. Gap of 2+ days or first ever: 1.
    """
    if last_done is None:
        return 1
    gap = (today - last_done).days
    if gap < 0:
        raise ValueError("today is before the last completed date")
    if gap == 0:
        return max(streak, 1)
    if gap == 1:
        return streak + 1
    return 1
