"""
InteriorDesignOS · Parser · Input Normalizer（Phase 3 §4）

统一：路径、编码、单位、坐标、文本编码、文件名。
输出统一 InputContext，供后续 Builder 使用。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from agents.parser.input_detector import InputType
from agents.parser.input_loader import LoadedInput


@dataclass
class InputContext:
    """归一化后的统一输入上下文（只读语义的解析前置产物）。"""

    loaded: LoadedInput
    normalized_path: str
    encoding: str = "utf-8"
    units: str = "mm"
    coordinate_system: str = "world"
    filename: str = ""
    raw_text: str = ""
    raw_json: Optional[Any] = field(default=None, repr=False)

    @property
    def input_type(self) -> InputType:
        return self.loaded.input_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "normalized_path": self.normalized_path,
            "encoding": self.encoding,
            "units": self.units,
            "coordinate_system": self.coordinate_system,
            "filename": self.filename,
            "input_type": self.loaded.input_type.value,
        }


def normalize(loaded: LoadedInput) -> InputContext:
    """将已加载输入归一化为统一上下文。

    - 路径：解析为绝对路径
    - 编码：文本默认 utf-8
    - 单位：默认 mm
    - 坐标：默认 world
    - 文件名：取 basename
    - 文本类：尝试读取内容（JSON 解析为对象作为几何提示，不在此做业务解析）
    """
    p = loaded.path.resolve()
    ctx = InputContext(
        loaded=loaded,
        normalized_path=str(p),
        filename=p.name,
    )
    if loaded.input_type is InputType.TEXT:
        try:
            ctx.raw_text = p.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            ctx.raw_text = ""
        # JSON：尝试解析为对象，供 model_builder 作为几何提示（不校验业务）
        if p.suffix.lower() == ".json":
            try:
                ctx.raw_json = json.loads(ctx.raw_text)
            except (json.JSONDecodeError, ValueError):
                ctx.raw_json = None
    return ctx


__all__ = ["InputContext", "normalize"]
