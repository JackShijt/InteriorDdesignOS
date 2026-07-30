"""tests.cad.test_dwg_roundtrip · Phase 12.6 · DWG Round-Trip 闭环验证。

链路：
    LayoutModel → DrawingModel → CAD Adapter → DWG
        → load_dwg → GeneratedModel → ValidationReport（Compare LayoutModel）
"""
from __future__ import annotations

import copy

import pytest

from agents.drawing.agent import DrawingAgent
from runtime.orchestrator.task_planner import ProjectRequirement
from runtime.pipeline.cad_export import (export_drawing_to_dwg,
                                         read_dwg_to_generated_model,
                                         round_trip_validate,
                                         run_dwg_round_trip)
from runtime.pipeline.stage_builders import (build_design_spec,
                                             build_layout_model,
                                             build_original_model)

REQUIREMENT = {
    "project_id": "rt001",
    "name": "RoundTrip 测试",
    "area": 100.0,
    "story": 1,
    "style": "现代简约",
    "rooms": [
        {"name": "客厅", "type": "LIVING", "area": 30.0},
        {"name": "主卧", "type": "BEDROOM", "area": 20.0},
        {"name": "厨房", "type": "KITCHEN", "area": 10.0},
    ],
}


@pytest.fixture()
def layout_model():
    req = ProjectRequirement.from_dict(REQUIREMENT)
    original = build_original_model(req)
    spec = build_design_spec(original, req)
    return build_layout_model(spec, req)


@pytest.fixture()
def drawing_model(layout_model):
    # 与 GeometryAgent 输出等价的几何视图（scale=1.0，坐标不变）
    geometry = {
        "rooms": layout_model["rooms"],
        "walls": layout_model["walls"],
        "doors": layout_model["doors"],
        "windows": layout_model["windows"],
        "furniture": [],
        "units": "mm",
    }
    return DrawingAgent.build_drawing_model(geometry)


class TestDWGRoundTrip:
    def test_dwg_generated_and_readable(self, tmp_path, drawing_model):
        dwg = tmp_path / "rt001.dwg"
        report = export_drawing_to_dwg(drawing_model, str(dwg),
                                       project_id="rt001",
                                       preferred_backend="mock")
        assert dwg.exists()
        assert report["backend"] == "mock"

        generated = read_dwg_to_generated_model(str(dwg), project_id="rt001")
        assert generated["dwg_path"] == str(dwg)
        assert generated["counts"]["entities"] > 0
        assert generated["counts"]["dimensions"] == 3  # 每房间一条

    def test_round_trip_validation_passes(self, tmp_path, drawing_model,
                                          layout_model):
        result = run_dwg_round_trip(drawing_model, layout_model,
                                    str(tmp_path / "rt001.dwg"),
                                    project_id="rt001",
                                    preferred_backend="mock")
        validation = result["validation"]
        assert validation["passed"] is True, validation["checks"]

        by_name = {c["check"]: c for c in validation["checks"]}
        # 房间数量
        assert by_name["room_count"]["expected"] == 3
        assert by_name["room_count"]["passed"]
        # 墙数量（3 房间 × 4 边）
        assert by_name["wall_count"]["expected"] == 12
        assert by_name["wall_count"]["passed"]
        # 门窗数量
        assert by_name["door_count"]["passed"]
        assert by_name["window_count"]["passed"]
        # 坐标误差 / 尺寸误差
        assert validation["max_coordinate_error_mm"] <= 1.0
        assert validation["max_dimension_error_mm"] <= 1.0

    def test_counts_match_layout(self, tmp_path, drawing_model, layout_model):
        result = run_dwg_round_trip(drawing_model, layout_model,
                                    str(tmp_path / "rt001.dwg"),
                                    project_id="rt001",
                                    preferred_backend="mock")
        counts = result["generated_model"]["counts"]
        assert counts["walls"] == len(layout_model["walls"])
        assert counts["doors"] == len(layout_model["doors"])
        assert counts["windows"] == len(layout_model["windows"])

    def test_validation_detects_mismatch(self, tmp_path, drawing_model,
                                         layout_model):
        """篡改 LayoutModel（多一堵墙 + 平移坐标）→ 验证必须失败。"""
        mutated = copy.deepcopy(layout_model)
        mutated["walls"].append({
            "id": "W999",
            "start": {"x": 0, "y": 0}, "end": {"x": 1000, "y": 0},
            "thickness": 200,
        })
        mutated["walls"][0]["start"]["x"] += 50.0  # 超出 1mm 容差

        result = run_dwg_round_trip(drawing_model, mutated,
                                    str(tmp_path / "rt001.dwg"),
                                    project_id="rt001",
                                    preferred_backend="mock")
        validation = result["validation"]
        assert validation["passed"] is False
        by_name = {c["check"]: c for c in validation["checks"]}
        assert not by_name["wall_count"]["passed"]
        assert not by_name["coordinate_error"]["passed"]

    def test_round_trip_with_autocad_preference_degrades(self, tmp_path,
                                                         drawing_model,
                                                         layout_model):
        """首选 autocad（MCP 未连接）→ 降级 mock，闭环仍成立。"""
        result = run_dwg_round_trip(drawing_model, layout_model,
                                    str(tmp_path / "rt001.dwg"),
                                    project_id="rt001",
                                    preferred_backend="autocad")
        assert result["export"]["backend"] == "mock"
        assert result["export"]["degraded"] is True
        assert result["validation"]["passed"] is True
