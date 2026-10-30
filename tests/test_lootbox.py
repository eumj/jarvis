import random
from collections import Counter

import pytest

from jarvis.rewards import (BOX_COST, GRADES, ITEM_POOL, SLOTS,
                            InsufficientPoints, open_box)


def test_pool_covers_every_grade_and_slot():
    for grade in GRADES:
        for slot in SLOTS:
            assert ITEM_POOL[(grade, slot)], (grade, slot)


def test_open_box_deducts_cost_and_returns_valid_item():
    item, left = open_box(BOX_COST + 5, random.Random(1))
    assert left == 5
    assert item.grade in GRADES and item.slot in SLOTS
    assert item.name in ITEM_POOL[(item.grade, item.slot)]


def test_same_seed_same_item():
    a, _ = open_box(BOX_COST, random.Random(42))
    b, _ = open_box(BOX_COST, random.Random(42))
    assert a == b


def test_insufficient_points_rejected():
    with pytest.raises(InsufficientPoints):
        open_box(BOX_COST - 1, random.Random(0))


def test_grade_distribution_is_roughly_as_configured():
    rng = random.Random(7)
    n = 5000
    counts = Counter(open_box(BOX_COST, rng)[0].grade for _ in range(n))
    assert counts["일반"] / n == pytest.approx(0.60, abs=0.04)
    assert counts["레전더리"] / n == pytest.approx(0.03, abs=0.015)
    assert set(counts) == set(GRADES)
