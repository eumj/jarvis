import random
from datetime import date

import pytest

from jarvis import models
from jarvis.cli import run
from jarvis.rewards import BOX_COST, InsufficientPoints


def rich_state(points=BOX_COST * 3):
    s = models.State()
    s.points = points
    return s


def test_buy_box_spends_points_and_stores_item():
    s = rich_state(BOX_COST + 7)
    item = models.buy_box(s, random.Random(1))
    assert s.points == 7
    assert s.inventory == [{"name": item.name, "grade": item.grade, "slot": item.slot}]


def test_buy_box_without_points_changes_nothing():
    s = rich_state(BOX_COST - 1)
    with pytest.raises(InsufficientPoints):
        models.buy_box(s, random.Random(1))
    assert s.points == BOX_COST - 1 and s.inventory == []


def test_duplicates_are_counted():
    s = rich_state()
    s.inventory = [{"name": "청바지", "grade": "일반", "slot": "바지"}] * 2
    assert models.inventory_summary(s)[0][1] == 2


def test_summary_lists_rarest_first():
    s = rich_state()
    s.inventory = [{"name": "청바지", "grade": "일반", "slot": "바지"},
                   {"name": "영웅의 왕관", "grade": "레전더리", "slot": "악세사리"}]
    assert models.inventory_summary(s)[0][0]["grade"] == "레전더리"


def test_equip_replaces_same_slot():
    s = rich_state()
    s.inventory = [{"name": "흰 티셔츠", "grade": "일반", "slot": "옷"},
                   {"name": "가죽 재킷", "grade": "희귀", "slot": "옷"}]
    models.equip_item(s, "흰 티셔츠")
    models.equip_item(s, "가죽 재킷")
    assert s.equipped == {"옷": "가죽 재킷"}


def test_equip_unowned_item_rejected():
    with pytest.raises(KeyError):
        models.equip_item(rich_state(), "용의 갑옷")


def test_cli_box_inventory_equip_flow(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_DATA", str(tmp_path / "s.json"))
    s = rich_state()
    models.save(s)
    assert run(["open-box"], rng=random.Random(3)) == 0
    name = models.load().inventory[0]["name"]
    assert run(["equip", name]) == 0
    assert run(["inventory"]) == 0
    out = capsys.readouterr().out
    assert "상자 오픈" in out and "(착용 중)" in out
    assert models.load().points == BOX_COST * 2


def test_cli_open_box_without_points(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_DATA", str(tmp_path / "s.json"))
    assert run(["open-box"], today=date(2026, 10, 30)) == 1
    assert "포인트가 부족" in capsys.readouterr().out
    assert run(["equip", "없는템"]) == 1
