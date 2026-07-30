"""
runtime.resume · 断点恢复管理器（Phase 11 §1 / §2）。

职责：封装“从中断处续跑”能力。实际恢复逻辑由 `E2EPipeline._resume`
完成（读取 Checkpoint -> 重建 TaskGraph 与内存产物 -> 继续调度）。
本管理器提供统一的判断与入口，使运行时目录结构 `runtime/resume` 完整。

约束：仅做编排，不修改任何 Schema；不接入真实 AutoCAD。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from runtime.checkpoint.checkpoint import CheckpointManager
from runtime.pipeline.e2e_pipeline import E2EPipeline
from runtime.project_runtime import ProjectRuntime


class ResumeManager:
    """判断是否可以恢复，并从中断处恢复执行。"""

    def __init__(self, workspace_root, backend: str = "mock", logger=None,
                 max_workers: int = 4, auto_approve: bool = True):
        self.workspace_root = workspace_root
        self.backend = backend
        self.logger = logger
        self.max_workers = max_workers
        self.auto_approve = auto_approve
        self._rt = ProjectRuntime(workspace_root)

    def can_resume(self, project_id: str) -> bool:
        """是否存在可恢复的断点。"""
        return CheckpointManager(self._rt.project_dir(project_id)).has()

    def resume(self, requirement: Any, event_bus=None) -> Dict[str, Any]:
        """从中断处恢复执行，返回与正常 run 一致的结果字典。"""
        ep = E2EPipeline(
            workspace_root=self.workspace_root, backend=self.backend,
            logger=self.logger, max_workers=self.max_workers,
            auto_approve=self.auto_approve, event_bus=event_bus)
        return ep.run(requirement, resume=True)


__all__ = ["ResumeManager"]
