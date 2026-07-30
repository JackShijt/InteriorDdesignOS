"""版本一致性校验测试（Phase 5 §9/§11 Version Check）。"""
import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from professional.validator import validate_models

EXAMPLE = json.loads(
    (REPO_ROOT / "schemas" / "examples" / "ProfessionalModel.example.json")
    .read_text(encoding="utf-8"))
LAYOUT = json.loads(
    (REPO_ROOT / "schemas" / "examples" / "LayoutModel.example.json")
    .read_text(encoding="utf-8"))


def test_layout_version_mismatch_between_models():
    a = copy.deepcopy(EXAMPLE)
    b = copy.deepcopy(EXAMPLE)
    b["discipline"] = "HVAC"
    b["layout_model_version"] = "v2"
    report = validate_models([a, b], LAYOUT)
    assert report["passed"] is False
    assert any("layout_model_version 不一致" in e
               for e in report["version_errors"])


def test_layout_version_mismatch_with_layout_model():
    a = copy.deepcopy(EXAMPLE)
    a["layout_model_version"] = "v9"
    report = validate_models([a], LAYOUT)  # LAYOUT 为 v1
    assert report["passed"] is False
    assert any("model_version" in e for e in report["version_errors"])


def test_schema_version_mismatch_between_models():
    a = copy.deepcopy(EXAMPLE)
    b = copy.deepcopy(EXAMPLE)
    b["discipline"] = "FURNITURE"
    b["metadata"]["schema_version"] = "2.0"
    report = validate_models([a, b], LAYOUT)
    assert report["passed"] is False
    assert any("schema_version 不一致" in e for e in report["version_errors"])


def test_consistent_versions_pass():
    a = copy.deepcopy(EXAMPLE)
    b = copy.deepcopy(EXAMPLE)
    b["discipline"] = "CEILING"
    report = validate_models([a, b], LAYOUT)
    assert report["version_errors"] == []
    assert report["passed"] is True
