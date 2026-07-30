"""
InteriorDesignOS · Parser · Input 类型识别（Phase 3 §2）

自动识别输入类型，返回 InputType。
识别依据：扩展名为主，未知扩展名时回退到魔数（magic bytes）猜测。
业务判断不得写在 orchestrator（§2）——识别逻辑全部在此模块。
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class InputType(str, Enum):
    """Parser 支持识别的输入类型。"""

    DWG = "DWG"
    DXF = "DXF"
    PDF = "PDF"
    IMAGE = "IMAGE"      # PNG / JPG / JPEG
    TEXT = "TEXT"        # JSON / TXT
    ZIP = "ZIP"
    UNKNOWN = "UNKNOWN"

    def is_supported(self) -> bool:
        """是否为其明确支持的类型（UNKNOWN 视为不支持）。"""
        return self is not InputType.UNKNOWN

    def is_text(self) -> bool:
        return self is InputType.TEXT


# 扩展名 -> 输入类型
_EXT_MAP: dict[str, "InputType"] = {
    ".dwg": InputType.DWG,
    ".dxf": InputType.DXF,
    ".pdf": InputType.PDF,
    ".png": InputType.IMAGE,
    ".jpg": InputType.IMAGE,
    ".jpeg": InputType.IMAGE,
    ".json": InputType.TEXT,
    ".txt": InputType.TEXT,
    ".zip": InputType.ZIP,
}

# 魔数（文件头）-> 输入类型，用于未知扩展名时的回退识别
_MAGIC_MAP: list[tuple[bytes, "InputType"]] = [
    (b"%PDF", InputType.PDF),
    (b"\x89PNG\r\n\x1a\n", InputType.IMAGE),
    (b"\xff\xd8\xff", InputType.IMAGE),
    (b"PK\x03\x04", InputType.ZIP),
]


def detect_input_type(path) -> "InputType":
    """根据路径识别输入类型。"""
    p = Path(path)
    ext = p.suffix.lower()
    if ext in _EXT_MAP:
        return _EXT_MAP[ext]
    # 未知扩展名：读取文件头魔数猜测
    try:
        with p.open("rb") as f:
            head = f.read(16)
    except OSError:
        return InputType.UNKNOWN
    for magic, itype in _MAGIC_MAP:
        if head.startswith(magic):
            return itype
    return InputType.UNKNOWN


def input_type_for_mime(mime: str) -> "InputType":
    """根据 MIME 类型推断输入类型（用于已有 MIME 的场景）。"""
    mime = (mime or "").lower()
    if mime in ("application/acad", "image/vnd.dwg", "application/x-dwg"):
        return InputType.DWG
    if mime.endswith("/dxf") or mime == "image/vnd.dxf":
        return InputType.DXF
    if mime == "application/pdf":
        return InputType.PDF
    if mime.startswith("image/"):
        return InputType.IMAGE
    if mime in ("application/json", "text/plain", "text/csv"):
        return InputType.TEXT
    if "zip" in mime or mime.endswith("/zip"):
        return InputType.ZIP
    return InputType.UNKNOWN


__all__ = ["InputType", "detect_input_type", "input_type_for_mime"]
