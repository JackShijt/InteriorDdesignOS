"""
InteriorDesignOS · Parser · Input Loader（Phase 3 §3）

职责：
- 加载文件
- 检查存在性
- 计算文件大小
- 记录 Hash（sha256）
- 记录 MIME

禁止解析业务（仅做 IO 与元数据收集）。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from agents.parser.exceptions import FatalError
from agents.parser.input_detector import InputType, detect_input_type


# 扩展名 -> MIME（轻量映射，避免引入额外依赖）
_MIME_EXT: Dict[str, str] = {
    ".dwg": "application/acad",
    ".dxf": "application/dxf",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".json": "application/json",
    ".txt": "text/plain",
    ".zip": "application/zip",
}


@dataclass
class LoadedInput:
    """已加载输入文件的元数据快照（不含业务内容）。"""

    path: Path
    exists: bool
    size_bytes: int
    file_hash: str
    mime_type: str
    input_type: InputType

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "file_hash": self.file_hash,
            "mime_type": self.mime_type,
            "input_type": self.input_type.value,
        }


def _mime_for(path: Path) -> str:
    return _MIME_EXT.get(path.suffix.lower(), "application/octet-stream")


def load_input(path) -> LoadedInput:
    """加载并收集输入文件元数据。

    文件不存在 / 非文件 -> 抛出 FatalError（不可重试，立即中止）。
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise FatalError(f"输入文件不存在或不是普通文件: {p}")
    data = p.read_bytes()
    file_hash = hashlib.sha256(data).hexdigest()
    itype = detect_input_type(p)
    mime = _mime_for(p)
    return LoadedInput(
        path=p,
        exists=True,
        size_bytes=len(data),
        file_hash=file_hash,
        mime_type=mime,
        input_type=itype,
    )


__all__ = ["LoadedInput", "load_input"]
