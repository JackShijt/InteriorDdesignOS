"""
InteriorDesignOS · Core Logging（Phase 5.1）

Agent 侧的最小日志抽象：professional/ 禁止 import runtime.logger，
统一通过本模块的 AgentLogger 协议注入（Runtime 可注入 UnifiedLogger，
两者鸭子类型兼容：runtime(action, **f) / agent(...) / error(action, error, **f)）。
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

_FILE_FOR_LEVEL = {
    "runtime": "runtime.log",
    "agent": "agent.log",
    "error": "error.log",
}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


class NullLogger:
    """空日志器：无副作用（Agent 默认值，保证 core 无强制 IO）。"""

    def runtime(self, action: str, **fields: Any) -> None:  # noqa: D401
        pass

    def agent(self, action: str, **fields: Any) -> None:
        pass

    def error(self, action: str, error: Any = None, **fields: Any) -> None:
        pass

    def info(self, action: str, **fields: Any) -> None:
        pass


class JsonFileLogger(NullLogger):
    """轻量 JSON 行日志器（格式与 runtime.UnifiedLogger 对齐；线程安全）。"""

    def __init__(self, log_dir: Path):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _write(self, level: str, action: str, **fields: Any) -> None:
        record: Dict[str, Any] = {"timestamp": _now_iso(), "level": level,
                                  "action": action}
        for key in ("project_id", "agent", "task_id", "status", "stage"):
            if key in fields:
                record[key] = fields.pop(key)
        if fields:
            record["extra"] = fields
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            with open(self._log_dir / _FILE_FOR_LEVEL.get(level, "runtime.log"),
                      "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def runtime(self, action: str, **fields: Any) -> None:
        self._write("runtime", action, **fields)

    def agent(self, action: str, **fields: Any) -> None:
        self._write("agent", action, **fields)

    def error(self, action: str, error: Any = None, **fields: Any) -> None:
        err_info = {"type": type(error).__name__, "message": str(error)}
        self._write("error", action, error=err_info, **fields)

    def info(self, action: str, **fields: Any) -> None:
        self.runtime(action, **fields)


def build_logger(log_dir: Optional[Path] = None,
                 logger: Any = None) -> Any:
    """日志器工厂：显式注入优先；给定 log_dir 时落盘；否则 Null。"""
    if logger is not None:
        return logger
    if log_dir is not None:
        return JsonFileLogger(Path(log_dir))
    return NullLogger()


__all__ = ["NullLogger", "JsonFileLogger", "build_logger"]
