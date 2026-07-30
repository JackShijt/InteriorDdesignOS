"""
runtime.workspace · Workspace 生命周期管理（Phase 11 §4）。

职责：
  为 `workspace/projects/<project_id>/` 建立标准目录结构，并在每次 Agent
  产出后保存产物，并记录§4要求的六元元数据：
    - 输入版本 (input_version)
    - 输出版本 (output_version)
    - Agent
    - Task ID
    - Timestamp
    - Status

标准结构（Phase 11 §4）：
  project/
  ├── project.json
  tasks/
  ├── task_graph.json
  ├── task_history.json
  models/
  ├── original_model/
  ├── design_spec/
  ├── layout_model/
  ├── professional_models/
  ├── geometry_model/
  ├── drawing_model/
  └── generated_model/
  cad/
  ├── input/
  ├── output/
  validation/
  ├── reports/
  logs/

本模块不依赖任何 Agent 实现，仅负责落盘与记录，遵守 PROJECT_RULES 最高约束。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 标准阶段 -> 模型子目录（Phase 11 §4 要求的目录 + 必要扩展）
MODEL_SUBDIRS: Dict[str, str] = {
    "ORIGINAL_MODEL": "original_model",
    "DESIGN_SPEC": "design_spec",
    "LAYOUT": "layout_model",
    "PROFESSIONAL_DEEPENING": "professional_models",
    "GEOMETRY": "geometry_model",
    "DRAWING": "drawing_model",
    "VALIDATION": "validation_reports",
    "EXPORT": "generated_model",
}

_REQUIRED_SUBDIRS = [
    "tasks",
    "models",
    "cad/input",
    "cad/output",
    "validation/reports",
    "logs",
]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


class WorkspaceManager:
    """Workspace 生命周期：目录初始化与产物落盘（含六元元数据）。"""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.tasks_dir = self.project_dir / "tasks"
        self.models_dir = self.project_dir / "models"
        self.cad_dir = self.project_dir / "cad"
        self.validation_dir = self.project_dir / "validation"
        self.logs_dir = self.project_dir / "logs"

    # ---- 初始化 ----
    def init(self, project_meta: Dict[str, Any]) -> Path:
        """创建标准目录结构并写入 project.json。"""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        for sub in _REQUIRED_SUBDIRS:
            (self.project_dir / sub).mkdir(parents=True, exist_ok=True)
        for sub in MODEL_SUBDIRS.values():
            (self.models_dir / sub).mkdir(parents=True, exist_ok=True)
        self._write_json(self.project_dir / "project.json", project_meta)
        return self.project_dir

    # ---- 路径 ----
    def model_dir(self, stage: str) -> Path:
        sub = MODEL_SUBDIRS.get(stage, "generated_model")
        d = self.models_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        return d

    def artifact_path(self, stage: str, filename: str) -> Path:
        return self.model_dir(stage) / filename

    # ---- 产物保存（§4 六元元数据） ----
    def save_artifact(
        self,
        stage: str,
        agent: str,
        task_id: str,
        model_dict: Dict[str, Any],
        output_schema: str,
        *,
        output_version: str = "v1",
        input_version: str = "",
        status: str = "COMPLETED",
        dependencies: Optional[List[str]] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """保存一次 Agent 输出，并追加一条六元元数据记录到 task_history.json。

        返回该条记录（供 Checkpoint / 测试断言）。
        """
        fname = filename or f"{stage.lower()}_{task_id}.json"
        path = self.artifact_path(stage, fname)
        self._write_json(path, model_dict)

        record = {
            "task_id": task_id,
            "agent": agent,
            "stage": stage,
            "output_schema": output_schema,
            "output_file": str(path.relative_to(self.project_dir)),
            "input_version": input_version,
            "output_version": output_version,
            "timestamp": _now_iso(),
            "status": status,
            "dependencies": list(dependencies or []),
        }
        self._append_history(record)
        return record

    def _append_history(self, record: Dict[str, Any]) -> None:
        history_path = self.tasks_dir / "task_history.json"
        history: List[Dict[str, Any]] = []
        if history_path.exists():
            try:
                history = json.loads(history_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                history = []
        history.append(record)
        self._write_json(history_path, history)

    # ---- 辅助落盘 ----
    def save_task_graph(self, graph_dict: Dict[str, Any]) -> Path:
        path = self.tasks_dir / "task_graph.json"
        self._write_json(path, graph_dict)
        return path

    def save_checkpoint(self, checkpoint_dict: Dict[str, Any]) -> Path:
        path = self.tasks_dir / "checkpoint.json"
        self._write_json(path, checkpoint_dict)
        return path

    def save_cad(self, category: str, filename: str,
                 content: Any, *, as_json: bool = True) -> Path:
        """保存 CAD 中间/产物（input/output）。"""
        d = self.cad_dir / category
        d.mkdir(parents=True, exist_ok=True)
        path = d / filename
        if as_json:
            self._write_json(path, content)
        else:
            path.write_text(str(content), encoding="utf-8")
        return path

    def save_validation_report(self, filename: str,
                               report: Dict[str, Any]) -> Path:
        path = self.validation_dir / "reports" / filename
        self._write_json(path, report)
        return path

    def read_artifact(self, stage: str, filename: str) -> Dict[str, Any]:
        path = self.artifact_path(stage, filename)
        return json.loads(path.read_text(encoding="utf-8"))

    def history(self) -> List[Dict[str, Any]]:
        path = self.tasks_dir / "task_history.json"
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    # ---- 内部 ----
    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


__all__ = ["WorkspaceManager", "MODEL_SUBDIRS"]
