# Design Agent · Prompt / 处理逻辑

Design Agent 不调用 LLM，采用**确定性规则解析**（可测试、可复现）：

1. 用 `requirement_parser` 把用户需求抽取为 `UserRequirement`（家庭/风格/预算/房间/采光/收纳/特殊需求）。
2. 用 `constraint_parser` 从 OriginalModel 提取 `ConstraintSet`（承重墙/窗/层高/面积/朝向）。
3. `style_planner` 映射风格标签（允许多个，来自 §5 枚举）。
4. `budget_planner` 给出预算等级（LOW/MEDIUM/HIGH/PREMIUM）+ 分配建议。
5. `family_analyzer` 推导家庭画像。
6. `material_planner` 给出材料偏好（禁止品牌）。
7. 组装 `DesignSpec`，用 `validator` 按 `design_spec.schema.json` 校验。
8. 落盘 `design_spec.json`（v1）与 `checkpoint_design_v1.json`，返回统一 `Result`。

所有关键词规则在对应 `*_parser.py` / `*_planner.py` 中显式定义，无隐式 LLM 行为。
