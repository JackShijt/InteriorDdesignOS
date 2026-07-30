"""Schema Validation 测试（Phase 3 §6 / §13）。"""
import json
from pathlib import Path

from agents.parser.exceptions import ValidationError
from agents.parser.input_detector import InputType
from agents.parser.model_builder import build_original_model
from agents.parser.validator import assert_valid, validate_original_model

REPO = Path(__file__).resolve().parent.parent.parent


def _valid():
    return build_original_model("p", "t", InputType.TEXT,
                                {"confidence": 0.3, "quality_score": 30,
                                 "validation_passed": True})


def test_valid_passes():
    assert validate_original_model(_valid()) == []


def test_missing_required_fails():
    m = _valid()
    del m["metadata"]
    errs = validate_original_model(m)
    assert errs and any("metadata" in e for e in errs)
    try:
        assert_valid(m)
        raise AssertionError("应抛出 ValidationError")
    except ValidationError:
        pass


def test_bad_nested_fails():
    m = _valid()
    m["walls"] = [{"id": "W"}]  # 缺 start/end/thickness
    errs = validate_original_model(m)
    assert errs
    try:
        assert_valid(m)
        raise AssertionError("应抛出 ValidationError")
    except ValidationError:
        pass


def test_sample_json_validates():
    sample = REPO / "examples" / "input" / "sample_json" / "sample.json"
    m = json.loads(sample.read_text(encoding="utf-8"))
    assert validate_original_model(m) == []
