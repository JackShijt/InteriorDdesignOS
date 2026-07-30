"""Constraint Parser 测试（Phase 4 §4）。"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents.design.constraint_parser import parse_constraints


def _load(name: str) -> dict:
    data = json.loads((REPO_ROOT / "examples" / "design" / name).read_text(encoding="utf-8"))
    return data["original_model"]


def test_extracts_walls_windows_area_orientation():
    om = _load("three_room.json")
    cs = parse_constraints(om)
    assert cs["non_removable_walls"] == ["W01", "W02", "W03", "W04"]
    assert cs["load_bearing_walls"] == ["W01", "W02", "W03", "W04"]
    assert cs["windows"] == ["WIN01", "WIN02"]
    assert cs["area_m2"] == 40.0
    assert cs["ceiling_height_mm"] == 2800
    assert cs["orientation"] in ("北", "南", "东", "西", "待现场确认")


def test_missing_fields_marked_in_notes():
    om = _load("small_apartment.json")
    cs = parse_constraints(om)
    # 这些字段 DWG 未含，应留空并在 notes 标注
    assert cs["pipe_shafts"] == []
    assert cs["beams"] == []
    assert cs["columns"] == []
    assert "DWG 未含" in cs["notes"]


def test_invalid_input_raises():
    import pytest
    from agents.design.exceptions import ValidationError
    with pytest.raises(TypeError):
        parse_constraints("not a dict")
