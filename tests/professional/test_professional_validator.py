"""Professional Validator 聚合校验测试（Phase 5 §9/§11）。"""
import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from professional.validator import (ProfessionalValidator, validate_model,
                                    validate_models, validate_quality)

EXAMPLE = json.loads(
    (REPO_ROOT / "schemas" / "examples" / "ProfessionalModel.example.json")
    .read_text(encoding="utf-8"))
LAYOUT = json.loads(
    (REPO_ROOT / "schemas" / "examples" / "LayoutModel.example.json")
    .read_text(encoding="utf-8"))


def _second_model() -> dict:
    m = copy.deepcopy(EXAMPLE)
    m["discipline"] = "LIGHTING"
    m["metadata"]["agent"] = "lighting"
    return m


def test_aggregate_validation_passes_for_valid_models():
    report = validate_models([EXAMPLE, _second_model()], LAYOUT)
    assert report["passed"] is True
    assert report["checked"] == 2
    assert report["errors"] == {}
    assert report["version_errors"] == []
    assert set(report["disciplines"]) == {"ELECTRICAL", "LIGHTING"}


def test_invalid_quality_detected():
    bad = copy.deepcopy(EXAMPLE)
    bad["quality"]["validation_passed"] = False
    errs = validate_quality(bad)
    assert any("validation_passed" in e for e in errs)
    report = ProfessionalValidator().validate_all([bad], LAYOUT)
    assert report["passed"] is False
    assert "ELECTRICAL" in report["errors"]


def test_quality_range_checked():
    bad = copy.deepcopy(EXAMPLE)
    bad["quality"]["confidence"] = 2.0
    assert validate_quality(bad)


def test_schema_violation_detected_in_report():
    bad = copy.deepcopy(EXAMPLE)
    del bad["objects"]
    assert validate_model(bad), "缺少 objects 应产生 schema 错误"
    report = validate_models([bad], LAYOUT)
    assert report["passed"] is False


def test_empty_model_list_fails():
    report = validate_models([], LAYOUT)
    assert report["passed"] is False
    assert report["checked"] == 0
