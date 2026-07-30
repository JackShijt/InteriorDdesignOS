"""Requirement Parser 测试（Phase 4 §3）。"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents.design.requirement_parser import parse_requirement


def test_family_and_special_extraction():
    text = "三口之家，有老人和小孩，养了一只猫，常居家办公，预算中等，北欧风，强收纳"
    req = parse_requirement(text)
    assert req["family_hints"].get("children") is True
    assert req["family_hints"].get("elders") is True
    assert req["family_hints"].get("work_from_home") is True
    assert req["family_hints"].get("pets_keywords") == ["猫"]
    assert "Nordic" in req["style_hints"]
    assert "MEDIUM" in req["budget_hints"]
    assert "强收纳" in req["storage_hints"]
    assert "居家办公" in req["special"]


def test_style_and_budget_keywords():
    req = parse_requirement("想要轻奢风，预算充足，有儿童")
    assert "Luxury" in req["style_hints"]
    assert "HIGH" in req["budget_hints"]
    assert req["family_hints"].get("children") is True


def test_empty_requirement_returns_defaults():
    req = parse_requirement("")
    assert req["raw_text"] == ""
    assert req["notes"]  # 应有缺省说明
    assert req["style_hints"] == []
