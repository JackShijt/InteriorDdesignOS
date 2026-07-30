"""mcp.cad_adapter.cad_adapter · CAD Adapter 执行编排（Phase 13 §4）。

**本模块是唯一允许调用 AutoCAD MCP 的模块**（Drawing Agent / Geometry Agent
禁止直接调用，architecture.md §4 / §12 / Phase 13 最高约束）。

执行链路：
    DrawingModel / GeometryModel
        ↓ CommandMapper（Model → CAD Command）
        ↓ CADAdapter（唯一调用 AutoCAD MCP 的位置）
        ↓ AutoCADMCPClient → AutoCAD MCP → AutoCAD 2026
        ↓ DWG
        ↓ DWGBridge → GeneratedModel

约束：
- 不含任何设计判定 / 空间解释 / 合规逻辑（那属于 Agent 层）。
- 不修改 LayoutModel / GeometryModel / DrawingModel。
- 仅经 ``AutoCADMCPClient`` 与外部交互。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from mcp.cad_adapter.command_mapper import CommandMapper, make_command
from mcp.cad_adapter.dwg_bridge import DWGBridge, ReferenceDWGBridge
from mcp.cad_adapter.entity_mapper import EntityMapper
from mcp.cad_adapter.exceptions import (
    AutoCADConnectionError,
    CommandMappingError,
)

if TYPE_CHECKING:  # 仅类型标注，避免与 mcp.autocad 形成循环导入
    from mcp.autocad.autocad_mcp_client import AutoCADMCPClient


class CADAdapter:
    """DrawingModel / GeometryModel → AutoCAD 执行 → GeneratedModel。"""

    def __init__(
        self,
        client: AutoCADMCPClient,
        entity_mapper: Optional[EntityMapper] = None,
        dwg_bridge: Optional[DWGBridge] = None,
        mapper: Optional[CommandMapper] = None,
    ) -> None:
        self.client = client
        self.entity_mapper = entity_mapper or EntityMapper()
        self.dwg_bridge = dwg_bridge or ReferenceDWGBridge()
        self.mapper = mapper or CommandMapper()

    # ---- 命令构建 --------------------------------------------------------
    def build_commands(
        self,
        drawing_model: Union[Dict[str, Any], Any],
        geometry_model: Optional[Union[Dict[str, Any], Any]] = None,
        dwg_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """DrawingModel → CAD Command 列表（尾附 SAVE_DWG）。"""
        commands = self.mapper.map_drawing_model(drawing_model, geometry_model)
        # SAVE_DWG 由 Adapter 追加（不属于 Model 翻译范畴）
        save = make_command(
            "SAVE_DWG",
            {"path": dwg_path or "output.dwg"},
            source_model="DrawingModel",
            source_version="1.0",
            command_id=self.mapper._next_id(),
        )
        commands.append(save)
        return commands

    # ---- 执行（命令级，供 Test 3 直接喂命令） ---------------------------
    def run(
        self,
        commands: List[Dict[str, Any]],
        dwg_path: str,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """直接执行一组 CAD Command → DWG → GeneratedModel。"""
        if not commands:
            raise CommandMappingError("命令列表为空")
        # 确保 SAVE_DWG 存在且路径正确
        commands = self._ensure_save_dwg(commands, dwg_path)
        try:
            self.client.connect()
        except AutoCADConnectionError:
            raise
        try:
            executed: List[Dict[str, Any]] = []
            for cmd in commands:
                result = self.client.send_command(cmd)
                self._track(cmd, result)
                executed.append({"command": cmd, "result": result})
        finally:
            self.client.disconnect()

        generated = self.dwg_bridge.generate_model(dwg_path, project_id=project_id)
        return {
            "dwg_path": dwg_path,
            "command_count": len(commands),
            "executed": executed,
            "entity_mapping": self.entity_mapper.entries(),
            "entity_mapping_size": self.entity_mapper.size(),
            "generated_model": generated,
        }

    # ---- 执行（模型级，供生产闭环） -------------------------------------
    def execute(
        self,
        drawing_model: Union[Dict[str, Any], Any],
        dwg_path: str,
        geometry_model: Optional[Union[Dict[str, Any], Any]] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """DrawingModel（+ 可选 GeometryModel）→ DWG → GeneratedModel。"""
        commands = self.build_commands(drawing_model, geometry_model, dwg_path)
        return self.run(commands, dwg_path, project_id=project_id)

    # ---- 内部辅助 --------------------------------------------------------
    def _ensure_save_dwg(self, commands: List[Dict[str, Any]], dwg_path: str):
        has_save = any(c.get("command_type") == "SAVE_DWG" for c in commands)
        if not has_save:
            commands = list(commands) + [make_command(
                "SAVE_DWG", {"path": dwg_path}, "DrawingModel", "1.0",
                command_id=self.mapper._next_id())]
        else:
            # 修正已有 SAVE_DWG 的 path
            for c in commands:
                if c.get("command_type") == "SAVE_DWG":
                    c["payload"]["path"] = dwg_path
        return commands

    def _track(self, command: Dict[str, Any], result: Dict[str, Any]) -> None:
        if not isinstance(result, dict):
            return
        handle = result.get("handle")
        if not handle:
            return
        payload = command.get("payload", {}) or {}
        ref = payload.get("entity_id") or payload.get("geometry_ref")
        if ref:
            self.entity_mapper.register(ref, handle)


__all__ = ["CADAdapter"]
