"""tests.integration.test_full_pipeline · 端到端流水线验证（Phase 8 §6）。

验证：
    Project 创建 -> Agent 执行 -> 模型生成 -> CAD Mock 执行 -> 文件输出
全程无需人工干预（验收 §8）。
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from runtime.pipeline import PipelineRunner  # noqa: E402
from models.geometry import GeometryModel  # noqa: E402
from models.drawing import DrawingModel  # noqa: E402
from models.generated import GeneratedModel  # noqa: E402


LAYOUT = {
    "metadata": {"project_id": "t", "agent": "layout", "task_id": "layout-t",
                 "timestamp": "2026-01-01T00:00:00+08:00", "schema_version": "1.0",
                 "status": "COMPLETED", "quality": {}},
    "version": {"model_version": "v1", "parent_version": "none"},
    "rooms": [
        {"room_id": "living", "name": "客厅", "type": "living",
         "boundary": {"type": "polygon", "points": [
             {"x": 0, "y": 0}, {"x": 6000, "y": 0},
             {"x": 6000, "y": 6000}, {"x": 0, "y": 6000}]},
         "area": 36, "perimeter": 24, "centroid": {"x": 3000, "y": 3000}},
    ],
    "walls": [
        {"wall_id": "w1", "start": {"x": 0, "y": 0}, "end": {"x": 6000, "y": 0},
         "thickness": 200, "type": "exterior", "layer": "WALL"},
    ],
    "doors": [
        {"door_id": "d1", "start": {"x": 1000, "y": 0}, "end": {"x": 1600, "y": 0},
         "width": 900, "swing": 90, "layer": "DOOR"},
    ],
    "windows": [
        {"window_id": "win1", "start": {"x": 2000, "y": 0}, "end": {"x": 3200, "y": 0},
         "width": 1200, "layer": "WIN"},
    ],
    "furniture": [
        {"item_id": "s1", "name": "沙发", "type": "SOFA", "position": {"x": 3000, "y": 3000},
         "size": {"width": 2000, "depth": 800}, "rotation": 0},
    ],
    "constraints": [],
}


def _run(tmp_path):
    runner = PipelineRunner(workspace_root=tmp_path, backend="mock")
    return runner.run(LAYOUT, project_id="demo", name="test")


def test_full_pipeline_creates_files(tmp_path):
    summary = _run(tmp_path)
    assert summary["status"] == "COMPLETED", summary.get("error")
    pd = Path(summary["project_dir"])
    for f in ("project.json", "LayoutModel.json", "GeometryModel.json",
              "DrawingModel.json", "drawing_command_log.json"):
        assert (pd / f).exists(), f"缺少输出文件: {f}"


def test_full_pipeline_generates_models(tmp_path):
    summary = _run(tmp_path)
    pd = Path(summary["project_dir"])
    geom = json.loads((pd / "GeometryModel.json").read_text(encoding="utf-8"))
    GeometryModel.from_dict(geom)
    draw = json.loads((pd / "DrawingModel.json").read_text(encoding="utf-8"))
    DrawingModel.from_dict(draw)
    gen = json.loads((pd / "GeneratedModel.json").read_text(encoding="utf-8"))
    GeneratedModel.from_dict(gen)

    # DrawingModel 必须包含图层 / 实体 / 尺寸
    assert draw["layers"], "DrawingModel 缺少 layers"
    assert draw["entities"], "DrawingModel 缺少 entities"
    assert draw["dimensions"], "DrawingModel 缺少 dimensions"


def test_full_pipeline_cad_mock_executed(tmp_path):
    summary = _run(tmp_path)
    pd = Path(summary["project_dir"])
    log = json.loads((pd / "drawing_command_log.json").read_text(encoding="utf-8"))
    assert log["backend"] == "mock"
    assert summary["command_count"] > 0


def test_full_pipeline_runs_without_human_intervention(tmp_path):
    summary = _run(tmp_path)
    assert summary["status"] == "COMPLETED"
    assert "error" not in summary
    # 模型版本链连续
    chain = json.loads((Path(summary["project_dir"]) / "model_chain.json").read_text())
    types = [c["model_type"] for c in chain["chain"]]
    assert types == ["layout", "geometry", "drawing", "generated"]
