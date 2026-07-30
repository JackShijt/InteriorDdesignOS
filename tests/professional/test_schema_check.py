"""ProfessionalModel Schema 校验测试（Phase 5 §4/§11 Schema Check）。"""
import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from professional.validator import (ProfessionalValidationError,
                                    assert_model_valid, validate_model)

SCHEMA = json.loads(
    (REPO_ROOT / "schemas" / "professional" / "professional_model.schema.json")
    .read_text(encoding="utf-8"))
EXAMPLE = json.loads(
    (REPO_ROOT / "schemas" / "examples" / "ProfessionalModel.example.json")
    .read_text(encoding="utf-8"))


def test_schema_has_required_public_fields():
    """§4：至少包含 metadata / layout_model_version / discipline /
    objects / constraints / quality。"""
    required = set(SCHEMA["required"])
    assert {"metadata", "layout_model_version", "discipline",
            "objects", "constraints", "quality"} <= required


def test_discipline_enum_covers_eight():
    enum = set(SCHEMA["properties"]["discipline"]["enum"])
    assert enum == {"ELECTRICAL", "PLUMBING", "LIGHTING", "CEILING",
                    "FLOORING", "HVAC", "CONSTRUCTION", "FURNITURE"}


def test_example_passes_schema():
    assert validate_model(EXAMPLE) == []
    assert_model_valid(EXAMPLE)  # 不抛异常


def test_missing_required_field_fails():
    for key in ("metadata", "layout_model_version", "discipline",
                "objects", "constraints", "quality"):
        bad = copy.deepcopy(EXAMPLE)
        del bad[key]
        assert validate_model(bad), f"缺少 {key} 应校验失败"


def test_cad_fields_forbidden():
    """禁止 CAD / DWG / Entity / Layer 字段（additionalProperties=false）。"""
    for cad_key in ("entities", "layers", "dwg", "drawing", "geometry"):
        bad = copy.deepcopy(EXAMPLE)
        bad[cad_key] = []
        errs = validate_model(bad)
        assert errs, f"顶层不应允许 CAD 字段 {cad_key}"


def test_invalid_discipline_fails():
    bad = copy.deepcopy(EXAMPLE)
    bad["discipline"] = "CAD"
    assert validate_model(bad)


def test_assert_model_valid_raises():
    bad = copy.deepcopy(EXAMPLE)
    bad["objects"] = [{"category": "switches"}]  # 缺 id
    try:
        assert_model_valid(bad)
        raise AssertionError("应当抛出 ProfessionalValidationError")
    except ProfessionalValidationError:
        pass
