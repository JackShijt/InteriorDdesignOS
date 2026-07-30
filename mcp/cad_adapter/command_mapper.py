"""mcp.cad_adapter.command_mapper · Model → CAD Command 映射（Phase 13 §6）。

职责边界（严格）：
- 只做 ``Model → Command`` 的纯结构翻译。
- 禁止修改 Geometry / Layout。
- 禁止判断设计合理性、空间关系、合规。
- 不接触 AutoCAD MCP（那属于 ``CADAdapter`` + ``AutoCADMCPClient``）。

映射规则（Phase 13 §6 / Test 2）：
- WALL  / DOOR / WINDOW  → CREATE_LINE
- FURNITURE             → CREATE_BLOCK
- DIMENSION             → CREATE_DIMENSION
- ANNOTATION            → CREATE_TEXT
- LAYER                 → CREATE_LAYER
- BLOCK                 → CREATE_BLOCK

GeometryModel 映射（Test 1）：
- lines      → CREATE_LINE
- polygons   → CREATE_POLYLINE（闭合）
- dimensions → CREATE_DIMENSION

所有命令符合 ``mcp/schemas/cad_tool.schema.json``（CAD Tool Command Contract）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mcp.cad_adapter.exceptions import (
    CommandMappingError,
    SchemaValidationError,
    UnsupportedCommandError,
)

# ---------------------------------------------------------------------------
# Contract 常量（与 cad_tool.schema.json 保持一致，单一来源）
# ---------------------------------------------------------------------------
COMMAND_TYPES: List[str] = [
    "CREATE_LINE",
    "CREATE_POLYLINE",
    "CREATE_RECTANGLE",
    "CREATE_TEXT",
    "CREATE_DIMENSION",
    "CREATE_BLOCK",
    "CREATE_LAYER",
    "SAVE_DWG",
    "OPEN_DWG",
    "READ_ENTITY",
]

STATUS_VALUES: List[str] = ["PENDING", "RUNNING", "COMPLETED", "FAILED"]

# DrawingModel 实体类型 → CAD command_type
ENTITY_TYPE_TO_COMMAND: Dict[str, str] = {
    "WALL": "CREATE_LINE",
    "DOOR": "CREATE_LINE",
    "WINDOW": "CREATE_LINE",
    "FURNITURE": "CREATE_BLOCK",
    "BLOCK": "CREATE_BLOCK",
    "ANNOTATION": "CREATE_TEXT",
    "DIMENSION": "CREATE_DIMENSION",
}

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "cad_tool.schema.json"


# ---------------------------------------------------------------------------
# 模型 → dict 兼容（DrawingModel / GeometryModel 既可为 dataclass 也可为 JSON dict）
# ---------------------------------------------------------------------------
def _as_dict(model: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
    if isinstance(model, dict):
        return model
    keys = (
        "metadata", "schema_version", "layout_model_version",
        "geometry_model_version", "coordinate_system", "units",
        "rooms", "layers", "entities", "dimensions", "annotations",
        "blocks", "sheets", "titleblock", "points", "lines", "polygons",
    )
    return {k: getattr(model, k, []) for k in keys}


def _source(model: Dict[str, Any]) -> tuple:
    meta = model.get("metadata") or {}
    model_name = meta.get("agent") or "UnknownModel"
    # agent 字段是生产者名（drawing / geometry），规范化为模型名
    source_model = {"drawing": "DrawingModel", "geometry": "GeometryModel"}.get(
        model_name, model_name)
    version = (
        model.get("schema_version")
        or meta.get("schema_version")
        or model.get("geometry_model_version")
        or "1.0"
    )
    return source_model, str(version)


# ---------------------------------------------------------------------------
# Command 构造与校验
# ---------------------------------------------------------------------------
def make_command(
    command_type: str,
    payload: Dict[str, Any],
    source_model: str,
    source_version: str,
    command_id: Optional[str] = None,
    status: str = "PENDING",
) -> Dict[str, Any]:
    """构造一条符合 CAD Tool Command Contract 的命令。"""
    if command_type not in COMMAND_TYPES:
        raise UnsupportedCommandError(f"不支持的 command_type: {command_type}")
    if status not in STATUS_VALUES:
        raise SchemaValidationError(f"非法 status: {status}")
    if command_id is None:
        raise CommandMappingError("command_id 不能为空")
    return {
        "command_id": command_id,
        "command_type": command_type,
        "source_model": source_model,
        "source_version": source_version,
        "payload": payload,
        "status": status,
    }


def validate_command(command: Dict[str, Any]) -> None:
    """轻量契约校验（不依赖第三方 jsonschema，必要时可扩展为完整 Draft 校验）。"""
    required = ("command_id", "command_type", "source_model",
                "source_version", "payload", "status")
    missing = [k for k in required if k not in command]
    if missing:
        raise SchemaValidationError(f"命令缺少字段: {missing}")
    if command["command_type"] not in COMMAND_TYPES:
        raise UnsupportedCommandError(
            f"command_type 越界: {command['command_type']}")
    if command["status"] not in STATUS_VALUES:
        raise SchemaValidationError(f"status 越界: {command['status']}")
    if not isinstance(command["payload"], dict):
        raise SchemaValidationError("payload 必须为 object")


def load_schema() -> Dict[str, Any]:
    """读取 cad_tool.schema.json（供完整 JSON Schema 校验使用）。"""
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 映射器
# ---------------------------------------------------------------------------
class CommandMapper:
    """DrawingModel / GeometryModel → CAD Command 列表。"""

    def __init__(self, id_prefix: str = "CMD") -> None:
        self._seq = 0
        self._id_prefix = id_prefix

    def _next_id(self) -> str:
        self._seq += 1
        return f"{self._id_prefix}-{self._seq:04d}"

    # ---- DrawingModel ----------------------------------------------------
    def map_drawing_model(
        self,
        drawing: Union[Dict[str, Any], Any],
        geometry: Optional[Union[Dict[str, Any], Any]] = None,
    ) -> List[Dict[str, Any]]:
        """DrawingModel → CAD Command。

        ``geometry`` 可选：提供时解析 ``geometry_ref`` 为真实坐标写入 payload
        （仅查表，不修改 Geometry）。
        """
        dm = _as_dict(drawing)
        source_model, source_version = _source(dm)
        geo_lookup = self._build_geometry_lookup(geometry) if geometry else {}

        commands: List[Dict[str, Any]] = []

        # 1) 图层
        for layer in dm.get("layers") or []:
            commands.append(make_command(
                "CREATE_LAYER",
                {"name": layer.get("name"), "color": layer.get("color", 7),
                 "line_type": layer.get("line_type", "Continuous")},
                source_model, source_version, command_id=self._next_id(),
            ))

        # 2) 实体（WALL/DOOR/WINDOW/FURNITURE/...）
        for ent in dm.get("entities") or []:
            ctype = ENTITY_TYPE_TO_COMMAND.get(ent.get("type"))
            if ctype is None:
                # 未知类型：不臆造命令，直接报错以保持契约严格
                raise CommandMappingError(
                    f"实体类型无法映射为 CAD 命令: {ent.get('type')}")
            payload = {
                "entity_id": ent.get("entity_id"),
                "geometry_ref": ent.get("geometry_ref"),
                "layer": ent.get("layer"),
            }
            self._attach_geometry(payload, ctype, geo_lookup,
                                  ent.get("geometry_ref"))
            commands.append(make_command(
                ctype, payload, source_model, source_version,
                command_id=self._next_id()))

        # 3) 标注
        for dim in dm.get("dimensions") or []:
            payload = {
                "geometry_ref": dim.get("geometry_ref"),
                "entity_id": dim.get("dimension_id"),
                "start": dim.get("start"),
                "end": dim.get("end"),
                "value": dim.get("value"),
                "unit": dim.get("unit", "mm"),
            }
            self._attach_geometry(payload, "CREATE_DIMENSION", geo_lookup,
                                  dim.get("geometry_ref"))
            commands.append(make_command(
                "CREATE_DIMENSION", payload, source_model, source_version,
                command_id=self._next_id()))

        # 4) 文字注释
        for anno in dm.get("annotations") or []:
            commands.append(make_command(
                "CREATE_TEXT",
                {"entity_id": anno.get("entity_id"), "text": anno.get("text"),
                 "position": anno.get("position")},
                source_model, source_version, command_id=self._next_id()))

        # 5) 块定义
        for blk in dm.get("blocks") or []:
            commands.append(make_command(
                "CREATE_BLOCK",
                {"entity_id": blk.get("block_id") or blk.get("entity_id"),
                 "block_ref": blk.get("name") or blk.get("block_ref"),
                 "layer": blk.get("layer")},
                source_model, source_version, command_id=self._next_id()))

        for cmd in commands:
            validate_command(cmd)
        return commands

    # ---- GeometryModel ---------------------------------------------------
    def map_geometry_model(
        self, geometry: Union[Dict[str, Any], Any]
    ) -> List[Dict[str, Any]]:
        """GeometryModel → CAD Command（Test 1：数量一致）。"""
        gm = _as_dict(geometry)
        source_model, source_version = _source(gm)
        commands: List[Dict[str, Any]] = []

        for line in gm.get("lines") or []:
            commands.append(make_command(
                "CREATE_LINE",
                {"geometry_ref": line.get("id"), "layer": line.get("layer_ref"),
                 "start": line.get("start"), "end": line.get("end")},
                source_model, source_version, command_id=self._next_id()))

        for pg in gm.get("polygons") or []:
            commands.append(make_command(
                "CREATE_POLYLINE",
                {"geometry_ref": pg.get("id"), "closed": True,
                 "points": pg.get("vertices")},
                source_model, source_version, command_id=self._next_id()))

        for dim in gm.get("dimensions") or []:
            commands.append(make_command(
                "CREATE_DIMENSION",
                {"geometry_ref": dim.get("id"), "start": dim.get("start"),
                 "end": dim.get("end"), "value": dim.get("value"),
                 "unit": dim.get("unit", "mm")},
                source_model, source_version, command_id=self._next_id()))

        for cmd in commands:
            validate_command(cmd)
        return commands

    # ---- 坐标解析辅助 ----------------------------------------------------
    @staticmethod
    def _build_geometry_lookup(
        geometry: Union[Dict[str, Any], Any]
    ) -> Dict[str, Dict[str, Any]]:
        gm = _as_dict(geometry)
        lookup: Dict[str, Dict[str, Any]] = {}
        for line in gm.get("lines") or []:
            lookup[line.get("id")] = {"start": line.get("start"),
                                      "end": line.get("end")}
        for pg in gm.get("polygons") or []:
            lookup[pg.get("id")] = {"vertices": pg.get("vertices")}
        for dim in gm.get("dimensions") or []:
            lookup[dim.get("id")] = {"start": dim.get("start"),
                                     "end": dim.get("end"),
                                     "value": dim.get("value")}
        return lookup

    @staticmethod
    def _attach_geometry(
        payload: Dict[str, Any], command_type: str,
        lookup: Dict[str, Dict[str, Any]], ref: Optional[str],
    ) -> None:
        if not ref or ref not in lookup:
            return
        info = lookup[ref]
        if command_type == "CREATE_LINE":
            payload["start"] = info.get("start")
            payload["end"] = info.get("end")
        elif command_type == "CREATE_DIMENSION":
            payload["start"] = info.get("start")
            payload["end"] = info.get("end")
            payload.setdefault("value", info.get("value"))


__all__ = [
    "COMMAND_TYPES", "STATUS_VALUES", "ENTITY_TYPE_TO_COMMAND",
    "make_command", "validate_command", "load_schema", "CommandMapper",
]
