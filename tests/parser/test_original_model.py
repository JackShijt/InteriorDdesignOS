"""OriginalModel Builder 测试（Phase 3 §5 / §13）。"""
from agents.parser.input_detector import InputType
from agents.parser.model_builder import build_original_model


def _quality():
    return {"confidence": 0.3, "quality_score": 30, "validation_passed": True}


def test_build_has_six_keys():
    m = build_original_model("p", "t", InputType.PDF, _quality())
    assert set(m.keys()) == {"metadata", "units", "coordinates",
                             "walls", "doors", "windows", "rooms"}


def test_default_geometry_empty():
    m = build_original_model("p", "t", InputType.IMAGE, _quality())
    assert m["walls"] == [] and m["doors"] == [] and m["windows"] == [] and m["rooms"] == []


def test_no_null_fields():
    m = build_original_model("p", "t", InputType.UNKNOWN, _quality())
    for v in m.values():
        assert v is not None


def test_hints_populate_geometry():
    hints = {"walls": [{"id": "W1", "start": [0, 0], "end": [1, 1], "thickness": 10}]}
    m = build_original_model("p", "t", InputType.TEXT, _quality(), hints=hints)
    assert m["walls"] == hints["walls"]
    # 未提供的几何仍为默认空数组
    assert m["doors"] == []


def test_metadata_fields():
    m = build_original_model("projX", "taskX", InputType.DWG, _quality())
    md = m["metadata"]
    assert md["project_id"] == "projX"
    assert md["agent"] == "parser"
    assert md["task_id"] == "taskX"
    assert md["status"] == "COMPLETED"
