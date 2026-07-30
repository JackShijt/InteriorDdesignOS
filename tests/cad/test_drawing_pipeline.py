"""Phase 6 §6/§9 · Drawing Pipeline 端到端测试。

验证：
- DrawingAgent 不直接操作 CAD（经 CommandQueue → CADSession → Adapter）
- 使用 examples 跑通默认（mock 后端）：输出 drawing_command_log.json
- 非法图层名触发 CAD 校验失败
- autocad 后端（Phase 6 占位）不可执行 → 优雅失败
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core.context import AgentContext
from agents.drawing import DrawingAgent

EXAMPLE_DRAWING = (Path(__file__).resolve().parents[2]
                   / "schemas" / "examples" / "DrawingModel.example.json")


def _workspace_root() -> Path:
    return Path(tempfile.mkdtemp()) / "workspace"


def test_drawing_agent_runs_against_mock_backend():
    ws_root = _workspace_root()
    ctx = AgentContext(project_id="P1", task_id="t1", stage="DRAWING")
    agent = DrawingAgent(workspace_root=ws_root, backend="mock")
    result = agent.run(ctx)

    assert result.success, result.messages
    log_path = ws_root / "projects" / "P1" / "cad" / "drawing_command_log.json"
    assert log_path.exists(), "DrawingAgent 未输出 drawing_command_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8"))
    assert log["backend"] == "mock"
    assert log["command_count"] > 0
    assert ctx.outputs.get("drawing_command_log") == str(log_path)
    assert ctx.outputs["backend"] == "mock"


def test_drawing_agent_rejects_illegal_layer():
    ws_root = _workspace_root()
    bad_model = {
        "metadata": {"project_id": "P2"},
        "layers": [{"name": "wall", "color": 7, "line_type": "Continuous"}],
        "entities": [],
    }
    ctx = AgentContext(project_id="P2", task_id="t2", stage="DRAWING",
                       inputs={"drawing_model": bad_model})
    agent = DrawingAgent(workspace_root=ws_root)
    result = agent.run(ctx)
    assert result.success is False
    assert any("非法 layer" in m or "校验失败" in m for m in result.messages)


def test_drawing_agent_autocad_backend_fails_gracefully():
    ws_root = _workspace_root()
    ctx = AgentContext(project_id="P3", task_id="t3", stage="DRAWING")
    agent = DrawingAgent(workspace_root=ws_root, backend="autocad")
    result = agent.run(ctx)
    # Phase 6：AutoCAD 后端只占位，connect 抛 NotImplementedError
    assert result.success is False


def test_drawing_agent_builds_expected_command_types():
    ws_root = _workspace_root()
    ctx = AgentContext(project_id="P4", task_id="t4", stage="DRAWING")
    agent = DrawingAgent(workspace_root=ws_root, backend="mock")
    agent.run(ctx)
    log = json.loads(
        (ws_root / "projects" / "P4" / "cad"
         / "drawing_command_log.json").read_text(encoding="utf-8"))
    ops = {r["op"] for r in log["log"]}
    # DrawingModel 至少应产生图层 + 墙体多段线 + 门弧 + 尺寸 + 文字 + 块
    assert "create_layer" in ops
    assert "draw_polyline" in ops
    assert "draw_arc" in ops
    assert "create_dimension" in ops
    assert "insert_block" in ops
