"""agents.lighting · 照明深化 Agent（Phase 9 §2）。

输入：LayoutModel
输出：LightingModel（强类型 dict）

业务：依据房间面积 / 类型规则派生灯具、照明开关与照明回路。
禁止：直接输出 DWG / 调用 AutoCAD。
"""
import math
from typing import Any, Dict, List

from core.context import AgentContext, BaseAgent, Result
from models.professional.lighting import LightingModel


class LightingAgent(BaseAgent):
    agent_name = "lighting"
    version = "1.0"

    def run(self, context: AgentContext) -> Result:
        layout = context.inputs.get("layout_model") or {}
        try:
            content = self.transform(layout)
            model = LightingModel(
                discipline="LIGHTING",
                fixtures=content["fixtures"],
                switches=content["switches"],
                circuits=content["circuits"],
                summary=content["summary"],
            )
            model.stamp(context, producer_agent=self.agent_name)
            msg = (f"Lighting: {len(content['fixtures'])} 灯具 / "
                   f"{len(content['switches'])} 开关 / {len(content['circuits'])} 回路")
            return Result(success=True, output_model=model.to_dict(), messages=[msg])
        except Exception as e:  # noqa: BLE001
            return Result(success=False, messages=[f"LightingAgent 失败：{e}"])

    # ------------------------------------------------------------------ #
    @staticmethod
    def transform(layout: Dict[str, Any]) -> Dict[str, Any]:
        rooms = layout.get("rooms", [])
        fixtures: List[Dict[str, Any]] = []
        switches: List[Dict[str, Any]] = []
        circuits: List[Dict[str, Any]] = []
        for i, room in enumerate(rooms, 1):
            rid = room.get("room_id", f"R{i}")
            name = room.get("name", "")
            area = float(room.get("area", 0) or 0)
            c = room.get("centroid") or {"x": 0, "y": 0}
            # 规则：每 12㎡ 一盏主灯，至少 1 盏
            fixture_n = max(1, math.ceil(area / 12))
            for f in range(fixture_n):
                fixtures.append({
                    "fixture_id": f"L-FIX-{rid}-{f + 1}",
                    "type": "RECESSED_DOWNLIGHT",
                    "room_id": rid,
                    "room_name": name,
                    "position": {"x": c.get("x", 0), "y": c.get("y", 0)},
                    "layer": "LIGHT-FIXTURE",
                    "power_w": 36,
                })
            switches.append({
                "switch_id": f"L-SW-{rid}-1",
                "type": "DIMMER",
                "room_id": rid,
                "room_name": name,
                "position": {"x": c.get("x", 0), "y": c.get("y", 0)},
                "layer": "LIGHT-SWITCH",
            })
            circuits.append({
                "circuit_id": f"LC-{rid}",
                "purpose": f"{name} 照明",
                "rooms": [rid],
                "estimated_load_w": fixture_n * 36,
            })
        return {
            "fixtures": fixtures,
            "switches": switches,
            "circuits": circuits,
            "summary": {"fixture_count": len(fixtures),
                        "switch_count": len(switches),
                        "circuit_count": len(circuits)},
        }
