"""
InteriorDesignOS · Checkpoint

本模块遵守 PROJECT_RULES.md 的最高约束。

检查点（Phase 2 §8 / PROJECT_RULES §11）：
- 每完成一个 Stage，自动保存该阶段的产物到 workspace/projects/<id>/
    project.json / layout_v1.json / geometry_v1.json / drawing_v1.json / validation.json
- 版本自增（LayoutModel 版本链，PROJECT_RULES §4.4、§22）
- 支持恢复运行：从检查点读取已完成的产物，跳过已完成阶段

阶段 -> 工件种类映射（仅对产出数据模型的阶段做模型检查点）
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.event_bus import EventBus
from runtime.logger import UnifiedLogger
from runtime.project_runtime import ProjectRuntime
from agents.orchestrator.context_manager import ContextManager
from agents.orchestrator.error_handler import FatalError

# 阶段 -> ContextManager 工件种类
STAGE_TO_KIND = {
    "LAYOUT": "layout",
    "GEOMETRY": "geometry",
    "DRAWING": "drawing",
    "DWG_GENERATION": "drawing",
    "VALIDATION": "validation",
}


class Checkpoint:
    """阶段检查点：保存 / 恢复 / 列举。"""

    def __init__(self, context_manager: ContextManager, project_runtime: ProjectRuntime,
                 event_bus: EventBus, logger: UnifiedLogger):
        self._cm = context_manager
        self._pr = project_runtime
        self._bus = event_bus
        self._logger = logger

    def _next_version(self, project_id: str, kind: str) -> int:
        versions = self._cm.list_versions(project_id, kind)
        if not versions:
            return 1
        nums = []
        for p in versions:
            try:
                nums.append(int(p.stem.split("_v")[1]))
            except (IndexError, ValueError):
                continue
        return (max(nums) + 1) if nums else 1

    def save_stage(self, project_id: str, stage: str,
                   model: Optional[Dict[str, Any]]) -> Optional[Path]:
        """保存某阶段产物为检查点。返回保存路径（无对应模型类型时返回 None）。"""
        kind = STAGE_TO_KIND.get(stage)
        if kind is None or model is None:
            self._logger.runtime("checkpoint_skip", project_id=project_id,
                                 stage=stage, reason="no_model_kind")
            return None
        version = self._next_version(project_id, kind)
        path = self._cm.save(project_id, kind, model, version=version)
        self._logger.runtime("checkpoint_saved", project_id=project_id,
                             stage=stage, kind=kind, version=version, path=str(path))
        return path

    def save_project(self, project_id: str) -> Path:
        project = self._pr.load(project_id)
        if project is None:
            raise FatalError(f"Project 不存在，无法保存检查点: {project_id}")
        return self._cm.save_project(project_id, project)

    def restore(self, project_id: str) -> Dict[str, Optional[Dict[str, Any]]]:
        """读取所有已保存的最新产物（用于恢复运行）。"""
        return {
            "project": self._cm.load(project_id, "project"),
            "layout": self._cm.load(project_id, "layout"),
            "geometry": self._cm.load(project_id, "geometry"),
            "drawing": self._cm.load(project_id, "drawing"),
            "validation": self._cm.load(project_id, "validation"),
        }

    def list_checkpoints(self, project_id: str) -> List[str]:
        d = self._cm._project_dir(project_id)
        if not d.exists():
            return []
        return sorted(p.name for p in d.glob("*.json"))


__all__ = ["STAGE_TO_KIND", "Checkpoint"]
