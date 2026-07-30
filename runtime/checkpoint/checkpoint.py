"""
runtime.checkpoint · 断点检查点管理（Phase 11 §1 / §2）。

职责：
  在每个调度轮次后保存工程运行态，使 `runtime.resume` 能从中断处续跑。
  检查点内容（与磁盘产物配合，产物本身不重复存储，仅记录指针）：
    - requirement      （项目需求，用于恢复时重建上下文）
    - graph            （TaskGraph.to_dict()，含每个 task 的状态/依赖）
    - produced         （已产出 schema -> 落盘文件路径，恢复时重建内存对象）
    - messages         （运行日志）
    - conflict / approval （协调网关与人工审批状态）
    - status / saved_at

设计约束：不修改任何 Schema，不接入真实 AutoCAD；仅持久化编排态。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_CHECKPOINT_FILE = "checkpoint.json"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


class CheckpointManager:
    """保存 / 加载工程检查点。"""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)

    # ---- 保存 ----
    def save(
        self,
        *,
        project_id: str,
        requirement: Dict[str, Any],
        graph: Dict[str, Any],
        produced: List[Dict[str, Any]],
        messages: List[Dict[str, Any]],
        conflict: Optional[Dict[str, Any]] = None,
        approval: Optional[Dict[str, Any]] = None,
        status: str = "RUNNING",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        checkpoint = {
            "project_id": project_id,
            "saved_at": _now_iso(),
            "status": status,
            "requirement": requirement,
            "graph": graph,
            "produced": produced,
            "messages": messages,
            "conflict": conflict or {},
            "approval": approval or {},
            "extra": extra or {},
        }
        path = self.project_dir / "tasks" / _CHECKPOINT_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
        return checkpoint

    # ---- 加载 ----
    def load(self) -> Optional[Dict[str, Any]]:
        path = self.project_dir / "tasks" / _CHECKPOINT_FILE
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def has(self) -> bool:
        return (self.project_dir / "tasks" / _CHECKPOINT_FILE).exists()

    def clear(self) -> None:
        path = self.project_dir / "tasks" / _CHECKPOINT_FILE
        if path.exists():
            path.unlink()


__all__ = ["CheckpointManager"]
