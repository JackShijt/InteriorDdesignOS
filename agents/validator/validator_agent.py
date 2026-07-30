"""agents.validator · 专业深化校验 Agent（Phase 9 §5）。

输入：LayoutModel + ProfessionalModels（dict: name -> model dict）
输出：ValidationReport

检查：
  - 空间冲突：专业构件引用的 room_id 必须存在于 LayoutModel
  - 尺寸冲突：构件坐标应落在其所属房间边界内
  - 专业规则：湿区须有给排水器具；每个房间须有插座 / 灯具；回路负载上限

禁止：修改设计 / 修改布局 / 修改图纸（仅校验并产出报告）。
"""
from typing import Any, Dict, List

from core.context import AgentContext, BaseAgent, Result
from models.professional.base import ValidationReport

WET_ROOM_TYPES = {"kitchen", "bathroom", "balcony", "wc", "toilet", "utility"}


class ProfessionalValidator(BaseAgent):
    agent_name = "validator"
    version = "1.0"

    def run(self, context: AgentContext) -> Result:
        layout = context.inputs.get("layout_model") or {}
        prof = context.inputs.get("professional_models") or {}
        try:
            report = self.validate(layout, prof)
            model = ValidationReport(
                status=report["status"],
                checked_count=report["checked_count"],
                issues=report["issues"],
                rule_results=report["rule_results"],
                summary=report["summary"],
            )
            return Result(
                success=True,
                output_model=model.to_dict(),
                messages=[f"Validation: {report['status']} / "
                          f"{len(report['issues'])} issues"],
            )
        except Exception as e:  # noqa: BLE001
            return Result(success=False, messages=[f"ProfessionalValidator 失败：{e}"])

    # ------------------------------------------------------------------ #
    @staticmethod
    def validate(layout: Dict[str, Any],
                 prof: Dict[str, Any]) -> Dict[str, Any]:
        rooms = layout.get("rooms", [])
        room_index = {r.get("room_id"): r for r in rooms}
        issues: List[Dict[str, Any]] = []
        rule_results: List[Dict[str, Any]] = []

        # ---- 1) 空间冲突：引用未知房间 ----
        prof_room_ids: List[str] = []
        for agent, m in prof.items():
            for key in ("devices", "fixtures", "switches", "elements",
                        "supply_pipes", "drain_pipes", "planes", "elevations"):
                for item in m.get(key, []) or []:
                    rid = item.get("room_id")
                    if rid is not None:
                        prof_room_ids.append(rid)
                        if rid not in room_index:
                            ref = (item.get("device_id") or item.get("fixture_id")
                                   or item.get("pipe_id") or item.get("plane_id")
                                   or item.get("elevation_id")
                                   or item.get("element_id") or "?")
                            issues.append({
                                "severity": "ERROR",
                                "category": "SPATIAL_CONFLICT",
                                "subject": f"{agent}/{ref}",
                                "message": f"构件引用未知房间 {rid}",
                            })

        # ---- 2) 尺寸冲突：坐标落在房间边界外 ----
        for agent, m in prof.items():
            for key in ("devices", "fixtures", "switches", "elements"):
                for item in m.get(key, []) or []:
                    rid = item.get("room_id")
                    pos = item.get("position")
                    if rid in room_index and pos:
                        poly = (room_index[rid].get("boundary", {}) or {}).get("points", []) or []
                        if poly and not _point_in_polygon(pos, poly):
                            issues.append({
                                "severity": "WARN",
                                "category": "DIMENSION_CONFLICT",
                                "subject": f"{agent}/{item.get('device_id', item.get('fixture_id', '?'))}",
                                "message": f"坐标 {pos} 落在房间 {rid} 边界外",
                            })

        # ---- 3) 专业规则 ----
        plumbing = prof.get("plumbing", {})
        plumb_rooms = {f.get("room_id") for f in plumbing.get("fixtures", []) or []}
        electrical = prof.get("electrical", {})
        elec_rooms = {d.get("room_id") for d in electrical.get("devices", []) or []}
        lighting = prof.get("lighting", {})
        light_rooms = {f.get("room_id") for f in lighting.get("fixtures", []) or []}

        for r in rooms:
            rid = r.get("room_id")
            rtype = (r.get("type") or "").lower()
            # 湿区须有给排水器具
            if rtype in WET_ROOM_TYPES and rid not in plumb_rooms:
                issues.append({
                    "severity": "WARN",
                    "category": "PROFESSIONAL_RULE",
                    "subject": f"plumbing/{rid}",
                    "message": f"湿区 {r.get('name', rid)} 缺少给排水器具",
                })
            # 每个房间须有插座（阳台可放宽）
            if rtype != "balcony" and rid not in elec_rooms:
                issues.append({
                    "severity": "WARN",
                    "category": "PROFESSIONAL_RULE",
                    "subject": f"electrical/{rid}",
                    "message": f"房间 {r.get('name', rid)} 缺少插座",
                })
            # 每个房间须有灯具
            if rid not in light_rooms:
                issues.append({
                    "severity": "WARN",
                    "category": "PROFESSIONAL_RULE",
                    "subject": f"lighting/{rid}",
                    "message": f"房间 {r.get('name', rid)} 缺少灯具",
                })

        # 回路负载上限
        overload = 0
        for c in electrical.get("circuits", []) or []:
            if int(c.get("estimated_load_w", 0) or 0) > 3000:
                overload += 1
                issues.append({
                    "severity": "WARN",
                    "category": "PROFESSIONAL_RULE",
                    "subject": f"electrical/{c.get('circuit_id')}",
                    "message": f"回路 {c.get('circuit_id')} 负载 {c.get('estimated_load_w')}W 超过 3000W 上限",
                })
        rule_results.append({"rule": "circuit_load_limit", "violations": overload})

        errs = sum(1 for x in issues if x["severity"] == "ERROR")
        warns = sum(1 for x in issues if x["severity"] == "WARN")
        status = "FAIL" if errs else ("WARN" if warns else "PASS")
        return {
            "status": status,
            "checked_count": len(rooms) + len(prof_room_ids),
            "issues": issues,
            "rule_results": rule_results,
            "summary": {
                "error_count": errs,
                "warn_count": warns,
                "room_count": len(rooms),
                "professional_model_count": len(prof),
            },
        }


def _point_in_polygon(point: Dict[str, Any], polygon: List[Dict[str, Any]]) -> bool:
    """射线法判定点是否在多边形内（退化/单点时视为内部）。"""
    if not point or len(polygon) < 3:
        return True
    x, y = point.get("x", 0), point.get("y", 0)
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i].get("x", 0), polygon[i].get("y", 0)
        xj, yj = polygon[j].get("x", 0), polygon[j].get("y", 0)
        intersect = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi) + xi)
        if intersect:
            inside = not inside
        j = i
    return inside
