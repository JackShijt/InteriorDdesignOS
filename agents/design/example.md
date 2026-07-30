# Design Agent · Example（运行示例）

输入（用户需求）：
```
三口之家，有学龄儿童，夫妻常居家办公，北欧风，原木色浅灰，强收纳，采光好
```

经 Pipeline（`python main.py run demo --input sample.json --requirement "..."`）得到：

```json
{
  "version": "v1",
  "design_goal": "打造Nordic风格住宅（2人家庭，含儿童，需求：/居家办公），以 DesignSpec 固化全部设计决策。",
  "style": { "labels": ["Nordic"], "description": "浅木色 + 中性灰，强调自然采光与极简收纳" },
  "budget": { "level": "MEDIUM", "total_estimate": 300000, "allocation": [ ... ] },
  "family": { "adults": 2, "children": 1, "elders": 0, "pets": [], "work_from_home": true, "accessibility": false },
  "rooms": [ { "room_id": "R001", "name": "客厅", "function": "LIVING", "priority": "medium" } ],
  "constraints": { "load_bearing_walls": ["W01","W02","W03","W04"], "windows": ["WIN01"], "area_m2": 20.0, "orientation": "北" },
  "preferences": { "colors": ["原木色","浅灰"], "lighting_preference": "natural" },
  "materials": [ { "category": "地面", "spec": "木地板", "brand_recommended": false } ],
  "lighting": { "natural_light": "优先利用自然采光" },
  "storage": { "strategy": "全屋系统收纳" },
  "special_requirements": ["居家办公"]
}
```

完整示例见 `examples/design/DesignSpec.example.json` 与各输入 `examples/design/*.json`。
