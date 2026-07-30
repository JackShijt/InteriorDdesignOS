"""
tests.runtime.test_full_execution · Phase 11 完整运行时集成测试。

覆盖验收标准：
  - Project 创建
  - TaskGraph 生成
  - Agent 调度（含专业 Agent 并行）
  - Pipeline 执行
  - Checkpoint 保存
  - Resume 恢复
  - 最终 Deliverable 生成

同时验证：Agent 自动发现 / 契约校验 / Workspace 标准结构与六元元数据。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from runtime.pipeline import PipelineRunner
from runtime.project_runtime import ProjectRuntime
from runtime.workspace.workspace import WorkspaceManager, MODEL_SUBDIRS
from runtime.checkpoint.checkpoint import CheckpointManager
from runtime.registry import default_registry, validate_all
from runtime.orchestrator.task_planner import ProjectRequirement


REQUIREMENT = {
    "project_id": "test001",
    "name": "E2E 测试项目",
    "goal": "full_drawing",
    "area": 100.0,
    "story": 1,
    "style": "现代简约",
    "rooms": [
        {"name": "客厅", "type": "LIVING", "area": 20.0},
        {"name": "主卧", "type": "BEDROOM", "area": 16.0},
        {"name": "次卧", "type": "BEDROOM", "area": 12.0},
        {"name": "厨房", "type": "KITCHEN", "area": 8.0},
        {"name": "卫生间", "type": "BATHROOM", "area": 6.0},
        {"name": "阳台", "type": "BALCONY", "area": 8.0},
        {"name": "餐厅", "type": "DINING", "area": 10.0},
        {"name": "书房", "type": "STUDY", "area": 10.0},
        {"name": "玄关", "type": "ENTRY", "area": 4.0},
    ],
    "features": ["平面布局", "家具规划", "水电", "照明", "吊顶", "地面", "施工图"],
    "disciplines": [
        "electrical", "lighting", "plumbing", "ceiling",
        "construction", "elevation",
    ],
}


@pytest.fixture
def ws_root(tmp_path):
    root = tmp_path / "ws"
    root.mkdir(parents=True, exist_ok=True)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _req():
    return dict(REQUIREMENT)


# --------------------------------------------------------------------------
# 1) Agent 自动发现 + 契约校验（Phase 11 §3）
# --------------------------------------------------------------------------
def test_registry_discovery_and_validation():
    contracts = default_registry.list_agents()
    names = {c.agent_name for c in contracts}
    # 全部 Agent 由契约扫描而来，至少有几何/绘图/验证/若干专业
    assert "geometry" in names
    assert "drawing" in names
    assert "validator" in names
    # 契约校验全部通过
    problems = validate_all()
    assert problems == {}, f"契约校验未通过: {problems}"


# --------------------------------------------------------------------------
# 2) 完整执行：创建 / 规划 / 调度 / 执行 / 交付
# --------------------------------------------------------------------------
def test_full_execution(ws_root):
    runner = PipelineRunner(workspace_root=ws_root)
    result = runner.run_e2e(_req())

    # 状态
    assert result["status"] == "DELIVERED"

    # Project 创建
    rt = ProjectRuntime(ws_root)
    assert rt.exists("test001")
    proj = rt.load("test001")
    assert proj["state"] == "DELIVERED"

    # TaskGraph 生成 + 全流程产物
    arts = result["artifacts"]
    for needed in ("ORIGINAL_MODEL", "DESIGN_SPEC", "LAYOUT",
                   "GEOMETRY", "DRAWING", "VALIDATION", "EXPORT"):
        assert needed in arts, f"缺少产物阶段: {needed}"

    # 专业 Agent 全部调度并执行
    profs = set(result["professional_models"])
    assert {"electrical", "lighting", "plumbing", "ceiling",
            "construction", "elevation"}.issubset(profs)

    # CAD Mock 执行产生了命令
    assert result["cad_command_count"] > 0

    # Checkpoint 已保存
    cp = CheckpointManager(rt.project_dir("test001"))
    assert cp.has()

    # 最终 Deliverable 生成 + Workspace 标准结构
    proj_dir = Path(result["project_dir"])
    assert (proj_dir / "Deliverable.json").exists()
    assert (proj_dir / "project.json").exists()
    assert (proj_dir / "tasks" / "task_graph.json").exists()
    assert (proj_dir / "tasks" / "task_history.json").exists()
    for sub in MODEL_SUBDIRS.values():
        assert (proj_dir / "models" / sub).exists(), f"缺少模型目录: {sub}"
    assert (proj_dir / "cad" / "input").exists()
    assert (proj_dir / "cad" / "output").exists()
    assert (proj_dir / "validation" / "reports").exists()
    assert (proj_dir / "logs").exists()

    # 六元元数据完整
    history = json.loads(
        (proj_dir / "tasks" / "task_history.json").read_text(encoding="utf-8"))
    assert len(history) >= 7
    for rec in history:
        for key in ("task_id", "agent", "input_version",
                    "output_version", "timestamp", "status"):
            assert key in rec, f"元数据缺字段 {key}: {rec}"


# --------------------------------------------------------------------------
# 3) Checkpoint 保存 + Resume 恢复（Phase 11 §1/§2）
# --------------------------------------------------------------------------
def test_resume_from_checkpoint(ws_root):
    runner = PipelineRunner(workspace_root=ws_root)

    # 模拟在 parser 完成后中断
    with pytest.raises(RuntimeError):
        runner.run_e2e(_req(), fail_after="parser_task")

    rt = ProjectRuntime(ws_root)
    cp = CheckpointManager(rt.project_dir("test001"))
    assert cp.has()
    # 中断点后任务尚未完成
    data = cp.load()
    statuses = {t["task_id"]: t["status"] for t in data["graph"]["tasks"]}
    assert statuses["parser_task"] == "COMPLETED"
    assert statuses["design_task"] != "COMPLETED"

    # 从中断处恢复
    result = runner.run_e2e(_req(), resume=True)
    assert result["status"] == "DELIVERED"
    assert "EXPORT" in result["artifacts"]

    proj = rt.load("test001")
    assert proj["state"] == "DELIVERED"

    # 恢复后历史记录应包含 parser 与后续全部阶段
    proj_dir = Path(result["project_dir"])
    history = json.loads(
        (proj_dir / "tasks" / "task_history.json").read_text(encoding="utf-8"))
    stages = {rec["stage"] for rec in history}
    assert "ORIGINAL_MODEL" in stages
    assert "EXPORT" in stages


# --------------------------------------------------------------------------
# 4) Workspace 生命周期：每次 Agent 输出均落盘并带六元元数据
# --------------------------------------------------------------------------
def test_workspace_artifact_metadata(ws_root):
    runner = PipelineRunner(workspace_root=ws_root)
    result = runner.run_e2e(_req())
    proj_dir = Path(result["project_dir"])
    ws = WorkspaceManager(proj_dir)
    history = ws.history()
    # 每个阶段至少一条记录，且记录含六元元数据
    by_stage = {}
    for rec in history:
        by_stage.setdefault(rec["stage"], 0)
        by_stage[rec["stage"]] += 1
        for key in ("task_id", "agent", "input_version",
                    "output_version", "timestamp", "status"):
            assert key in rec
    # Layout 阶段有产物
    assert by_stage.get("LAYOUT", 0) >= 1
