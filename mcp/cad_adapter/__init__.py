"""mcp.cad_adapter · InteriorDesignOS → AutoCAD MCP 执行适配层（Phase 13）。

唯一允许调用 AutoCAD MCP 的模块集合；Agent 层不得直接调用（见 ARCHITECTURE §4）。
"""

from mcp.cad_adapter.cad_adapter import CADAdapter
from mcp.cad_adapter.command_mapper import CommandMapper, make_command, validate_command
from mcp.cad_adapter.dwg_bridge import DWGBridge, ReferenceDWGBridge
from mcp.cad_adapter.entity_mapper import EntityMapper

__all__ = [
    "CADAdapter", "CommandMapper", "make_command", "validate_command",
    "DWGBridge", "ReferenceDWGBridge", "EntityMapper",
]
