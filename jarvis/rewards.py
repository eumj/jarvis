"""Reward rules: XP, levels, streaks, loot boxes. Pure functions, no I/O."""
import random
from dataclasses import dataclass
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


# --- Loot box ---------------------------------------------------------

BOX_COST = 50
GRADES = ("일반", "희귀", "에픽", "레전더리")
GRADE_WEIGHTS = (60, 25, 12, 3)
SLOTS = ("옷", "바지", "악세사리")

ITEM_POOL = {
    ("일반", "옷"): ["흰 티셔츠", "회색 후드"],
    ("일반", "바지"): ["청바지", "면 반바지"],
    ("일반", "악세사리"): ["고무 팔찌", "털모자"],
    ("희귀", "옷"): ["가죽 재킷", "스트라이프 셔츠"],
    ("희귀", "바지"): ["카고 팬츠", "슬랙스"],
    ("희귀", "악세사리"): ["은목걸이", "선글라스"],
    ("에픽", "옷"): ["별빛 망토", "네온 점퍼"],
    ("에픽", "바지"): ["달빛 레깅스", "번개 무늬 바지"],
    ("에픽", "악세사리"): ["수정 귀걸이", "은하수 머플러"],
    ("레전더리", "옷"): ["용의 갑옷", "불사조 로브"],
    ("레전더리", "바지"): ["시간의 각반", "황금 정복자 바지"],
    ("레전더리", "악세사리"): ["영웅의 왕관", "세계수 반지"],
}


@dataclass(frozen=True)
class Item:
    name: str
    grade: str
    slot: str


class InsufficientPoints(Exception):
    pass


def open_box(points: int, rng: random.Random) -> tuple[Item, int]:
    """Spend BOX_COST points to draw one item. Returns (item, points_left)."""
    if points < BOX_COST:
        raise InsufficientPoints(f"need {BOX_COST} points, have {points}")
    grade = rng.choices(GRADES, weights=GRADE_WEIGHTS)[0]
    slot = rng.choice(SLOTS)
    name = rng.choice(ITEM_POOL[(grade, slot)])
    return Item(name, grade, slot), points - BOX_COST
