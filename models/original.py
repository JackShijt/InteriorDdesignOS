"""models.original · 原始输入模型。"""
from dataclasses import dataclass, field
from typing import Any, Dict

from models.base.model import Model


@dataclass
class OriginalModel(Model):
    source_type: str = "unknown"
    source_ref: str = ""
    raw_content: Dict[str, Any] = field(default_factory=dict)
    project_info: Dict[str, Any] = field(default_factory=dict)
