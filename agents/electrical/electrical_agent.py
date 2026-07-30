"""agents.electrical · 电气深化 Agent（Phase 9 §2）。

输入：LayoutModel
输出：ElectricalModel（强类型 dict）

业务：依据房间面积 / 类型规则派生插座、开关、回路与配电箱。
禁止：直接输出 DWG / 调用 AutoCAD（仅产生模型）。
"""
from typing import Any, Dict, List

from core.context import AgentContext, BaseAgent, Result
from models.professional.electrical import ElectricalModel


class ElectricalAgent(BaseAgent):
    agent_name = "electrical"
    version = "1.0"

    def run(self, context: AgentContext) -> Result:
        layout = context.inputs.get("layout_model") or {}
        try:
            content = self.transform(layout)
            model = ElectricalModel(
                discipline="ELECTRICAL",
                circuits=content["circuits"],
                devices=content["devices"],
                panels=content["panels"],
                summary=content["summary"],
            )
            model.stamp(context, producer_agent=self.agent_name)
            msg = (f"Electrical: {len(content['devices'])} 设备 / "
                   f"{len(content['circuits'])} 回路 / {len(content['panels'])} 配电箱")
            return Result(success=True, output_model=model.to_dict(), messages=[msg])
        except Exception as e:  # noqa: BLE001
            return Result(success=False, messages=[f"ElectricalAgent 失败：{e}"])

    # ------------------------------------------------------------------ #
    @staticmethod
    def transform(layout: Dict[str, Any]) -> Dict[str, Any]:
        rooms = layout.get("rooms", [])
        devices: List[Dict[str, Any]] = []
        circuits: List[Dict[str, Any]] = []
        for i, room in enumerate(rooms, 1):
            rid = room.get("room_id", f"R{i}")
            name = room.get("name", "")
            area = float(room.get("area", 0) or 0)
            c = room.get("centroid") or {"x": 0, "y": 0}
            # 规则：每 8㎡ 一个插座，至少 2 个
            socket_n = max(2, int(round(area / 8)))
            for s in range(socket_n):
                devices.append({
                    "device_id": f"E-SOCK-{rid}-{s + 1}",
                    "type": "SOCKET",
                    "room_id": rid,
                    "room_name": name,
                    "position": {"x": c.get("x", 0), "y": c.get("y", 0)},
                    "layer": "ELEC-SOCKET",
                    "spec": "10A 250V",
                })
            devices.append({
                "device_id": f"E-SW-{rid}-1",
                "type": "SWITCH",
                "room_id": rid,
                "room_name": name,
                "position": {"x": c.get("x", 0), "y": c.get("y", 0)},
                "layer": "ELEC-SWITCH",
                "spec": "双联",
            })
            circuits.append({
                "circuit_id": f"C-{rid}",
                "purpose": f"{name} 插座/照明",
                "rooms": [rid],
                "estimated_load_w": socket_n * 200 + 100,
            })
        panels = [{
            "panel_id": "PANEL-MAIN",
            "type": "distribution",
            "position": {"x": 0, "y": 0},
            "circuits": len(circuits),
        }]
        return {
            "circuits": circuits,
            "devices": devices,
            "panels": panels,
            "summary": {"device_count": len(devices),
                        "circuit_count": len(circuits),
                        "panel_count": len(panels)},
        }
