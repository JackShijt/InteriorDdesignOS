"""agents.plumbing · 给排水深化 Agent（Phase 9 §2）。

输入：LayoutModel
输出：PlumbingModel（强类型 dict）

业务：仅对湿区（kitchen / bathroom / balcony 等）派生给水管、排水管与卫生器具。
禁止：直接输出 DWG / 调用 AutoCAD。
"""
from typing import Any, Dict, List

from core.context import AgentContext, BaseAgent, Result
from models.professional.plumbing import PlumbingModel

WET_ROOM_TYPES = {"kitchen", "bathroom", "balcony", "wc", "toilet", "utility"}


class PlumbingAgent(BaseAgent):
    agent_name = "plumbing"
    version = "1.0"

    def run(self, context: AgentContext) -> Result:
        layout = context.inputs.get("layout_model") or {}
        try:
            content = self.transform(layout)
            model = PlumbingModel(
                discipline="PLUMBING",
                supply_pipes=content["supply_pipes"],
                drain_pipes=content["drain_pipes"],
                fixtures=content["fixtures"],
                water_heaters=content["water_heaters"],
                summary=content["summary"],
            )
            model.stamp(context, producer_agent=self.agent_name)
            msg = (f"Plumbing: {len(content['fixtures'])} 器具 / "
                   f"{len(content['supply_pipes'])} 给水管 / "
                   f"{len(content['drain_pipes'])} 排水管")
            return Result(success=True, output_model=model.to_dict(), messages=[msg])
        except Exception as e:  # noqa: BLE001
            return Result(success=False, messages=[f"PlumbingAgent 失败：{e}"])

    # ------------------------------------------------------------------ #
    @staticmethod
    def transform(layout: Dict[str, Any]) -> Dict[str, Any]:
        rooms = layout.get("rooms", [])
        supply: List[Dict[str, Any]] = []
        drain: List[Dict[str, Any]] = []
        fixtures: List[Dict[str, Any]] = []
        heaters: List[Dict[str, Any]] = []
        for i, room in enumerate(rooms, 1):
            rtype = (room.get("type") or "").lower()
            if rtype not in WET_ROOM_TYPES:
                continue
            rid = room.get("room_id", f"R{i}")
            name = room.get("name", "")
            c = room.get("centroid") or {"x": 0, "y": 0}
            start = {"x": 0, "y": 0}
            supply.append({
                "pipe_id": f"P-SUP-{rid}-C", "kind": "COLD",
                "start": start, "end": {"x": c.get("x", 0), "y": c.get("y", 0)},
                "diameter_mm": 25, "room_id": rid, "layer": "PLUMB-COLD",
            })
            if rtype in {"bathroom", "kitchen", "utility"}:
                supply.append({
                    "pipe_id": f"P-SUP-{rid}-H", "kind": "HOT",
                    "start": start, "end": {"x": c.get("x", 0), "y": c.get("y", 0)},
                    "diameter_mm": 20, "room_id": rid, "layer": "PLUMB-HOT",
                })
            drain.append({
                "pipe_id": f"P-DRN-{rid}", "kind": "DRAIN",
                "start": {"x": c.get("x", 0), "y": c.get("y", 0)},
                "end": {"x": 0, "y": 0}, "diameter_mm": 50,
                "room_id": rid, "layer": "PLUMB-DRAIN",
            })
            if rtype == "bathroom":
                fixtures += [
                    {"fixture_id": f"PL-WC-{rid}", "type": "TOILET", "room_id": rid,
                     "room_name": name, "position": {"x": c.get("x", 0), "y": c.get("y", 0)}, "layer": "PLUMB-FIXTURE"},
                    {"fixture_id": f"PL-WB-{rid}", "type": "WASHBASIN", "room_id": rid,
                     "room_name": name, "position": {"x": c.get("x", 0), "y": c.get("y", 0)}, "layer": "PLUMB-FIXTURE"},
                    {"fixture_id": f"PL-SH-{rid}", "type": "SHOWER", "room_id": rid,
                     "room_name": name, "position": {"x": c.get("x", 0), "y": c.get("y", 0)}, "layer": "PLUMB-FIXTURE"},
                ]
                heaters.append({"heater_id": f"WH-{rid}", "type": "STORAGE",
                                "capacity_l": 60, "room_id": rid,
                                "position": {"x": c.get("x", 0), "y": c.get("y", 0)}, "layer": "PLUMB-HEATER"})
            elif rtype == "kitchen":
                fixtures.append({"fixture_id": f"PL-SINK-{rid}", "type": "SINK",
                                 "room_id": rid, "room_name": name,
                                 "position": {"x": c.get("x", 0), "y": c.get("y", 0)}, "layer": "PLUMB-FIXTURE"})
            elif rtype == "balcony":
                fixtures.append({"fixture_id": f"PL-DRAIN-{rid}", "type": "FLOOR_DRAIN",
                                 "room_id": rid, "room_name": name,
                                 "position": {"x": c.get("x", 0), "y": c.get("y", 0)}, "layer": "PLUMB-FIXTURE"})
        return {
            "supply_pipes": supply,
            "drain_pipes": drain,
            "fixtures": fixtures,
            "water_heaters": heaters,
            "summary": {"fixture_count": len(fixtures),
                        "supply_count": len(supply),
                        "drain_count": len(drain)},
        }
