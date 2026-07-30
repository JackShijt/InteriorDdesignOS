"""mcp.cad_adapter.exceptions · CAD Adapter 异常体系（Phase 13）。

仅承载 CAD Adapter 执行链路的可观测错误，不含任何业务判定。
"""

from __future__ import annotations


class CADAdapterError(Exception):
    """CAD Adapter 执行链路根异常。"""


class CommandMappingError(CADAdapterError):
    """DrawingModel / GeometryModel → CAD Command 映射失败。"""


class EntityMappingError(CADAdapterError):
    """entity_id ↔ autocad_handle 映射失败。"""


class DWGBridgeError(CADAdapterError):
    """DWG → GeneratedModel 桥接失败。"""


class AutoCADConnectionError(CADAdapterError):
    """连接 AutoCAD MCP / AutoCAD 2026 失败。"""


class AutoCADExecutionError(CADAdapterError):
    """向 AutoCAD MCP 发送命令后，AutoCAD 侧执行失败。"""


class UnsupportedCommandError(CADAdapterError):
    """CAD Tool Command Contract 不支持的 command_type。"""


class SchemaValidationError(CADAdapterError):
    """CAD Command 不符合 cad_tool.schema.json 契约。"""


__all__ = [
    "CADAdapterError",
    "CommandMappingError",
    "EntityMappingError",
    "DWGBridgeError",
    "AutoCADConnectionError",
    "AutoCADExecutionError",
    "UnsupportedCommandError",
    "SchemaValidationError",
]
