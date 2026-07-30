"""DesignSpec 生成与 Schema 校验测试（Phase 4 §9、§1）。"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents.design.design import DesignAgent
from agents.design.validator import assert_valid
from agents.design.exceptions import ValidationError


def _load(name: str):
    data = json.loads((REPO_ROOT / "examples" / "design" / name).read_text(encoding="utf-8"))
    return data["original_model"], data["requirement"]


def test_generate_produces_valid_designspec():
    om, req = _load("three_room.json")
    agent = DesignAgent()
    result = agent.generate(om, req, "ds_test", "design-ds_test", save=False)
    assert result.success is True
    assert_valid(result.output_model)  # 不抛异常即通过


def test_example_file_validates():
    ex = json.loads((REPO_ROOT / "examples" / "design" / "DesignSpec.example.json")
                    .read_text(encoding="utf-8"))
    assert_valid(ex)


def test_invalid_spec_raises():
    bad = {"metadata": {}, "version": "v1"}  # 缺大量必填字段
    with pytest.raises(ValidationError):
        assert_valid(bad)


def test_assemble_forbidden_cad_fields_absent():
    om, req = _load("villa.json")
    agent = DesignAgent()
    spec = agent.assemble(om, req, "ds_cad", "design-ds_cad")
    blob = json.dumps(spec)
    for forbidden in ("CAD", "Geometry", "Drawing", "Layer", "Entity", "DWG"):
        # 仅检查顶层不应出现这些键（大小写敏感）
        assert forbidden not in spec, f"DesignSpec 禁止包含 {forbidden}"


def test_designspec_requires_version_field():
    om, req = _load("office.json")
    agent = DesignAgent()
    spec = agent.assemble(om, req, "ds_v", "design-ds_v")
    assert spec["version"] == "v1"
    assert "design_goal" in spec and spec["design_goal"]
