"""agents.elevation · 立面深化 Agent（Phase 9 §2）。

输入：LayoutModel
输出：ElevationModel（强类型 dict）

业务：依据房间与家具派生四向立面与立面构件（踢脚、柜体等）。
禁止：直接输出 DWG / 调用 AutoCAD。
"""
from typing import Any, Dict, List

from core.context import AgentContext, BaseAgent, Result
from models.professional.elevation import ElevationModel

DIRECTIONS = ["NORTH", "SOUTH", "EAST", "WEST"]


class ElevationAgent(BaseAgent):
    agent_name = "elevation"
    version = "1.0"

    def run(self, context: AgentContext) -> Result:
        layout = context.inputs.get("layout_model") or {}
        try:
            content = self.transform(layout)
            model = ElevationModel(
                discipline="ELEVATION",
                elevations=content["elevations"],
                elements=content["elements"],
                summary=content["summary"],
            )
            model.stamp(context, producer_agent=self.agent_name)
            msg = (f"Elevation: {len(content['elevations'])} 立面 / "
                   f"{len(content['elements'])} 构件")
            return Result(success=True, output_model=model.to_dict(), messages=[msg])
        except Exception as e:  # noqa: BLE001
            return Result(success=False, messages=[f"ElevationAgent 失败：{e}"])

    # ------------------------------------------------------------------ #
    @staticmethod
    def transform(layout: Dict[str, Any]) -> Dict[str, Any]:
        rooms = layout.get("rooms", [])
        elevations: List[Dict[str, Any]] = []
        elements: List[Dict[str, Any]] = []
        furniture = layout.get("furniture", [])
        for i, room in enumerate(rooms, 1):
            rid = room.get("room_id", f"R{i}")
            name = room.get("name", "")
            for d in DIRECTIONS:
                elevations.append({
                    "elevation_id": f"EL-{rid}-{d}",
                    "room_id": rid,
                    "room_name": name,
                    "direction": d,
                    "height_mm": 2600,
                    "layer": "ELEV-MAIN",
                })
            # 家具 -> 立面构件
            for f in furniture:
                # 简化：所有家具标注到其所属房间首面
                elements.append({
                    "element_id": f"EL-EL-{room.get('room_id', rid)}-{f.get('item_id', 'x')}",
                    "room_id": rid,
                    "source_type": f.get("type", "FURNITURE"),
                    "ref_id": f.get("item_id"),
                    "layer": "ELEV-ELEMENT",
                })
        return {
            "elevations": elevations,
            "elements": elements,
            "summary": {"elevation_count": len(elevations),
                        "element_count": len(elements)},
        }
