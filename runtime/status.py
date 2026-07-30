"""
Phase 3.5 §11 项目状态查询。

供 CLI 使用，输出：
  Current Project / Current Stage / Current Task / Progress
  / Running Agent / Elapsed Time
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from runtime.project_runtime import ProjectRuntime
from agents.orchestrator.task_graph import TaskGraph
from runtime.config import load_runtime_config

SUPPORTED_STAGES = ["INITIALIZATION", "INPUT_ANALYSIS", "ORIGINAL_MODEL", "DESIGN_SPEC"]


def report_status(project_id: str,
                  workspace_root: Optional[Path] = None,
                  config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = config or load_runtime_config()
    wr = workspace_root or cfg["workspace_root"]
    pr = ProjectRuntime(wr)
    if not pr.exists(project_id):
        return {"project_id": project_id, "exists": False}

    proj = pr.load(project_id)
    gp = pr.project_dir(project_id) / "task_graph.json"
    graph = TaskGraph.load(gp) if gp.exists() else TaskGraph()
    tasks = {tid: t.status for tid, t in graph.tasks.items()}

    # 当前任务：进行中（RUNNING/VALIDATING）的任务
    running = [tid for tid, s in tasks.items() if s in ("RUNNING", "VALIDATING")]
    current_task = running[0] if running else (next(iter(tasks)) if tasks else None)

    # 进度
    total = len(tasks) if tasks else len(SUPPORTED_STAGES)
    completed = sum(1 for s in tasks.values() if s == "COMPLETED")
    progress = (completed / total) if total else 0.0

    # 运行中的 Agent
    running_agent = None
    for tid, s in tasks.items():
        if s in ("RUNNING", "VALIDATING"):
            running_agent = graph.tasks[tid].agent

    # 耗时
    elapsed: Optional[float] = None
    created = proj.get("created_at")
    if created:
        try:
            elapsed = (datetime.now() - datetime.fromisoformat(created)).total_seconds()
        except Exception:
            elapsed = None

    return {
        "exists": True,
        "project_id": project_id,
        "project_name": proj.get("name"),
        "state": proj["state"],
        "current_stage": proj["current_stage"],
        "current_task": current_task,
        "tasks": tasks,
        "progress": progress,
        "running_agent": running_agent,
        "elapsed_seconds": elapsed,
    }


__all__ = ["report_status"]
