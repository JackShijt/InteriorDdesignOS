# Design Agent · Workflow（8 步工作流）

1. **解析需求** — `requirement_parser.parse_requirement(requirement)` → `UserRequirement`
2. **提取约束** — `constraint_parser.parse_constraints(original_model)` → `ConstraintSet`
3. **风格规划** — `style_planner.plan_style(req)` → `{labels, description}`
4. **预算规划** — `budget_planner.plan_budget(req, area)` → `{level, allocation}`
5. **家庭分析** — `family_analyzer.analyze_family(req)` → `FamilyProfile`
6. **材料规划** — `material_planner.plan_materials(req, constraints)` → 材料偏好列表
7. **组装 + 校验** — `design.assemble(...)` 生成 DesignSpec → `validator.assert_valid` 校验
8. **落盘 + 返回** — 写 `design_spec.json` / `checkpoint_design_v1.json`，返回统一 `Result`

校验失败立即中止（抛 `ValidationError`），不写 `design_spec.json`。
