"""
InteriorDesignOS · Project Runtime

本模块遵守 PROJECT_RULES.md 的最高约束。

Project 生命周期与持久化（Phase 2 §5 / PROJECT_RULES §11、§13）：
- 创建 / 加载 workspace/projects/<id>/project.json
- 维护 current_stage（12 阶段枚举，严格遵循顺序）
- 维护整体 state（Task State Machine 枚举）
- 支持断点恢复（读取 project.json 续跑）

数据契约遵循 schemas/project/project.schema.json：
  required: project_id / name / current_stage / state / created_at / updated_at
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from runtime import PROJECTS_DIR, ensure_workspace

# 12 阶段（与 schemas/core/task.schema.json、project.schema.json 枚举一致）
STAGES = [
    "INITIALIZATION",
    "INPUT_ANALYSIS",
    "ORIGINAL_MODEL",
    "DESIGN_SPEC",
    "LAYOUT",
    "PROFESSIONAL_DEEPENING",
    "GEOMETRY",
    "DRAWING",
    "DWG_GENERATION",
    "VALIDATION",
    "REPAIR",
    "EXPORT",
]

# 整体状态枚举（与 task schema 一致）
STATES = [
    "PENDING", "READY", "RUNNING", "WAITING_USER", "WAITING_AGENT",
    "RETRYING", "VALIDATING", "REPAIRING", "COMPLETED", "FAILED",
    "CANCELLED", "DELIVERED",
    # Phase 3.5 Project 生命周期状态（§2）：CREATED / INITIALIZING / WAITING
    "CREATED", "INITIALIZING", "WAITING",
]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


class ProjectRuntime:
    """工程运行时：负责 Project 对象的生命周期与落盘。"""

    def __init__(self, workspace_root: Optional[Path] = None):
        ensure_workspace()
        self._projects_dir = Path(workspace_root) / "projects" if workspace_root else PROJECTS_DIR

    # ---- 路径 ----
    def project_dir(self, project_id: str) -> Path:
        return self._projects_dir / project_id

    def project_json_path(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "project.json"

    # ---- 创建 / 加载 ----
    def create(self, project_id: str, name: str,
               current_stage: str = "INITIALIZATION",
               state: str = "RUNNING") -> Dict[str, Any]:
        if current_stage not in STAGES:
            raise ValueError(f"非法阶段: {current_stage}")
        if state not in STATES:
            raise ValueError(f"非法状态: {state}")
        d = self.project_dir(project_id)
        d.mkdir(parents=True, exist_ok=True)
        now = _now_iso()
        project = {
            "project_id": project_id,
            "name": name,
            "current_stage": current_stage,
            "state": state,
            "created_at": now,
            "updated_at": now,
        }
        self._write(project_id, project)
        return project

    def load(self, project_id: str) -> Optional[Dict[str, Any]]:
        p = self.project_json_path(project_id)
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def exists(self, project_id: str) -> bool:
        return self.project_json_path(project_id).exists()

    # ---- 更新 ----
    def update(self, project_id: str, **changes: Any) -> Dict[str, Any]:
        project = self.load(project_id)
        if project is None:
            raise FileNotFoundError(f"Project 不存在: {project_id}")
        for k, v in changes.items():
            if k in ("current_stage",) and v not in STAGES:
                raise ValueError(f"非法阶段: {v}")
            if k in ("state",) and v not in STATES:
                raise ValueError(f"非法状态: {v}")
            project[k] = v
        project["updated_at"] = _now_iso()
        self._write(project_id, project)
        return project

    def set_stage(self, project_id: str, stage: str) -> Dict[str, Any]:
        return self.update(project_id, current_stage=stage)

    def set_state(self, project_id: str, state: str) -> Dict[str, Any]:
        return self.update(project_id, state=state)

    # ---- 内部 ----
    def _write(self, project_id: str, project: Dict[str, Any]) -> None:
        p = self.project_json_path(project_id)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(project, f, ensure_ascii=False, indent=2)
