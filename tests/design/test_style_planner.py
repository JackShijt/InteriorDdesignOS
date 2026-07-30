"""Style Planner 测试（Phase 4 §5）。"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents.design.requirement_parser import parse_requirement
from agents.design.style_planner import plan_style


def test_multiple_labels_allowed():
    req = parse_requirement("北欧风，现代简约，带一点日式")
    style = plan_style(req)
    assert "Nordic" in style["labels"]
    assert "Modern" in style["labels"]
    assert "Japanese" in style["labels"]
    assert len(style["labels"]) >= 2


def test_empty_requirement_defaults_mixed():
    req = parse_requirement("")
    style = plan_style(req)
    assert style["labels"] == ["Mixed"]
    assert style["description"]


def test_all_enum_values_valid():
    from agents.design.style_planner import _ALLOWED
    allowed = {"Modern", "Minimal", "Nordic", "Japanese", "Industrial",
               "Chinese", "Luxury", "Mixed"}
    assert set(_ALLOWED) == allowed
