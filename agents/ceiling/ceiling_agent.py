"""agents.ceiling · 吊顶深化 Agent（Phase 9 §2）。

输入：LayoutModel
输出：CeilingModel（强类型 dict）

业务：依据房间边界派生吊顶平面、梁与开洞。
禁止：直接输出 DWG / 调用 AutoCAD。
"""
from typing import Any, Dict, List

from core.context import AgentContext, BaseAgent, Result
from models.professional.ceiling import CeilingModel


class CeilingAgent(BaseAgent):
    agent_name = "ceiling"
    version = "1.0"

    def run(self, context: AgentContext) -> Result:
        layout = context.inputs.get("layout_model") or {}
        try:
            content = self.transform(layout)
            model = CeilingModel(
                discipline="CEILING",
                planes=content["planes"],
                beams=content["beams"],
                openings=content["openings"],
                summary=content["summary"],
            )
            model.stamp(context, producer_agent=self.agent_name)
            msg = (f"Ceiling: {len(content['planes'])} 吊顶平面 / "
                   f"{len(content['openings'])} 开洞")
            return Result(success=True, output_model=model.to_dict(), messages=[msg])
        except Exception as e:  # noqa: BLE001
            return Result(success=False, messages=[f"CeilingAgent 失败：{e}"])

    # ------------------------------------------------------------------ #
    @staticmethod
    def transform(layout: Dict[str, Any]) -> Dict[str, Any]:
        rooms = layout.get("rooms", [])
        planes: List[Dict[str, Any]] = []
        openings: List[Dict[str, Any]] = []
        for i, room in enumerate(rooms, 1):
            rid = room.get("room_id", f"R{i}")
            name = room.get("name", "")
            boundary = (room.get("boundary", {}) or {}).get("points", []) or []
            planes.append({
                "plane_id": f"CL-{rid}",
                "room_id": rid,
                "room_name": name,
                "type": "GYPROCK_FLAT",
                "height_mm": 2600,
                "material": "石膏板",
                "boundary": {"points": boundary},
                "layer": "CEIL-PLANE",
            })
            for w in layout.get("windows", []):
                # 窗口在房间边界附近 -> 吊顶开洞（新风 / 窗帘盒）
                openings.append({
                    "opening_id": f"CL-OP-{rid}-{w.get('window_id', 'w')}",
                    "room_id": rid,
                    "source": "window",
                    "ref_id": w.get("window_id"),
                    "layer": "CEIL-OPENING",
                })
        beams = [{
            "beam_id": "BM-MAIN",
            "type": "STRUCTURAL",
            "size_mm": [300, 500],
            "layer": "CEIL-BEAM",
        }]
        return {
            "planes": planes,
            "beams": beams,
            "openings": openings,
            "summary": {"plane_count": len(planes),
                        "opening_count": len(openings)},
        }
