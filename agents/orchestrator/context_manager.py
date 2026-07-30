"""
InteriorDesignOS · Context Manager

本模块遵守 PROJECT_RULES.md 的最高约束。

上下文管理（Phase 2 §7 / PROJECT_RULES §4、§11）：
- 负责读取与保存工程级数据对象：
    Project / LayoutModel / GeometryModel / DrawingModel / ValidationReport
- ContextManager 禁止修改数据内容：仅做「读取」与「落盘」，不加工、不解释数据
  （加工由对应 Agent 负责，PROJECT_RULES §22 单一职责）

存储位置（默认为 workspace/projects/<id>/）：
    project.json            工程状态
    <kind>_v<n>.json        各模型版本化快照（LayoutModel 为 SSOT，遵循版本链）
    <kind>.json             最新版本软链接式副本
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from runtime import PROJECTS_DIR
from agents.orchestrator.error_handler import FatalError

# 受管工件种类（Phase 2 §7）
KINDS = ["project", "layout", "geometry", "drawing", "validation"]


class ContextManager:
    """工程上下文的读取 / 保存（只读语义：不修改数据内容）。"""

    def __init__(self, workspace_root: Optional[Path] = None):
        self._root = Path(workspace_root) if workspace_root else PROJECTS_DIR

    # ---- 路径 ----
    def _project_dir(self, project_id: str) -> Path:
        return self._root / project_id

    def _versioned_path(self, project_id: str, kind: str, version: int) -> Path:
        return self._project_dir(project_id) / f"{kind}_v{version}.json"

    def _latest_path(self, project_id: str, kind: str) -> Path:
        return self._project_dir(project_id) / f"{kind}.json"

    # ---- 保存（不修改传入对象，仅落盘）----
    def save(self, project_id: str, kind: str, model: Dict[str, Any],
             version: int = 1) -> Path:
        if kind not in KINDS:
            raise FatalError(f"未知工件种类: {kind}")
        d = self._project_dir(project_id)
        d.mkdir(parents=True, exist_ok=True)
        # 版本化快照
        vpath = self._versioned_path(project_id, kind, version)
        with open(vpath, "w", encoding="utf-8") as f:
            json.dump(model, f, ensure_ascii=False, indent=2)
        # 最新副本
        with open(self._latest_path(project_id, kind), "w", encoding="utf-8") as f:
            json.dump(model, f, ensure_ascii=False, indent=2)
        return vpath

    def save_project(self, project_id: str, project: Dict[str, Any]) -> Path:
        return self.save(project_id, "project", project, version=1)

    def save_layout(self, project_id: str, model: Dict[str, Any], version: int = 1) -> Path:
        return self.save(project_id, "layout", model, version=version)

    def save_geometry(self, project_id: str, model: Dict[str, Any], version: int = 1) -> Path:
        return self.save(project_id, "geometry", model, version=version)

    def save_drawing(self, project_id: str, model: Dict[str, Any], version: int = 1) -> Path:
        return self.save(project_id, "drawing", model, version=version)

    def save_validation(self, project_id: str, model: Dict[str, Any], version: int = 1) -> Path:
        return self.save(project_id, "validation", model, version=version)

    # ---- 读取 ----
    def load(self, project_id: str, kind: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        if kind not in KINDS:
            raise FatalError(f"未知工件种类: {kind}")
        path = (self._versioned_path(project_id, kind, version)
                if version is not None
                else self._latest_path(project_id, kind))
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_layout(self, project_id: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        return self.load(project_id, "layout", version)

    def load_geometry(self, project_id: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        return self.load(project_id, "geometry", version)

    def load_drawing(self, project_id: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        return self.load(project_id, "drawing", version)

    def load_validation(self, project_id: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        return self.load(project_id, "validation", version)

    def list_versions(self, project_id: str, kind: str) -> list:
        d = self._project_dir(project_id)
        if not d.exists():
            return []
        out = []
        for p in sorted(d.glob(f"{kind}_v*.json")):
            out.append(p)
        return out


__all__ = ["KINDS", "ContextManager"]
