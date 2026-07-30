"""
InteriorDesignOS · Unified Logger

本模块遵守 PROJECT_RULES.md 的最高约束。

统一日志（Phase 2 §10 / PROJECT_RULES §10）：
- 输出到 workspace/logs/：
    runtime.log   系统级运行日志
    agent.log     任务 / Agent 级日志
    error.log     错误日志
- 统一时间格式 ISO8601（PROJECT_RULES §10.2）
- 每条关键日志至少包含：timestamp / project_id / agent / task_id / action / status
- 禁止 print()（Phase 2 §11）；所有输出写入文件。
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from runtime import LOG_DIR, ensure_workspace

_LEVEL_RUNTIME = "runtime"
_LEVEL_AGENT = "agent"
_LEVEL_ERROR = "error"

_FILE_FOR_LEVEL = {
    _LEVEL_RUNTIME: "runtime.log",
    _LEVEL_AGENT: "agent.log",
    _LEVEL_ERROR: "error.log",
}


def _now_iso() -> str:
    # ISO8601（含本地时区偏移）
    return datetime.now().astimezone().isoformat()


class UnifiedLogger:
    """统一日志器：线程安全，按级别写入不同文件，禁止 print。"""

    def __init__(self, log_dir: Optional[Path] = None):
        ensure_workspace()
        self._log_dir = Path(log_dir) if log_dir else LOG_DIR
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _write(self, level: str, record: Dict[str, Any]) -> None:
        fname = _FILE_FOR_LEVEL.get(level, "runtime.log")
        line = json.dumps(record, ensure_ascii=False, default=str)
        # 纯文件写入，绝不 print
        with self._lock:
            with open(self._log_dir / fname, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def _record(self, level: str, action: str, **fields: Any) -> None:
        record = {
            "timestamp": _now_iso(),
            "level": level,
            "action": action,
        }
        # 注入约定字段（PROJECT_RULES §10.2）
        for key in ("project_id", "agent", "task_id", "status", "stage"):
            if key in fields:
                record[key] = fields.pop(key)
        if fields:
            record["extra"] = fields
        self._write(level, record)

    # ---- 公开 API ----
    def runtime(self, action: str, **fields: Any) -> None:
        self._record(_LEVEL_RUNTIME, action, **fields)

    def agent(self, action: str, agent: str, task_id: Optional[str] = None,
              project_id: Optional[str] = None, **fields: Any) -> None:
        self._record(_LEVEL_AGENT, action, agent=agent, task_id=task_id,
                     project_id=project_id, **fields)

    def error(self, action: str, error: Any, project_id: Optional[str] = None,
              agent: Optional[str] = None, task_id: Optional[str] = None,
              **fields: Any) -> None:
        err_info = {
            "type": type(error).__name__,
            "message": str(error),
        }
        self._record(_LEVEL_ERROR, action, project_id=project_id, agent=agent,
                     task_id=task_id, error=err_info, **fields)

    def info(self, action: str, **fields: Any) -> None:
        """通用信息日志（写入 runtime.log）。"""
        self.runtime(action, **fields)
