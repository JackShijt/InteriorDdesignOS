"""
InteriorDesignOS · Parser Agent

系统入口 Agent（Phase 3）：把 DWG / PDF / 图片 / 用户信息 等输入解析为统一数据模型
OriginalModel，经 Schema 校验、落盘 Workspace、写 Checkpoint，返回统一 Result。

Parser 不负责设计 / CAD 绘图（Phase 3 §14）。
"""

from agents.parser.parser import ParserAgent, run_parser
from agents.parser.input_detector import InputType
from agents.parser.exceptions import (
    RecoverableError, ValidationError, FatalError, OrchestratorError,
)

__all__ = [
    "ParserAgent",
    "run_parser",
    "InputType",
    "RecoverableError",
    "ValidationError",
    "FatalError",
    "OrchestratorError",
]
