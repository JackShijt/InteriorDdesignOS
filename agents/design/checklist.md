# Design Agent · Checklist（自检项）

- [ ] `OriginalModel` 可被读取（参数 / input_refs / Workspace 回退）
- [ ] `UserRequirement` 抽取包含家庭 / 风格 / 预算 / 特殊需求
- [ ] `ConstraintSet` 提取承重墙 / 窗 / 层高 / 面积 / 朝向
- [ ] `style.labels` 非空且均来自 §5 枚举
- [ ] `budget.level` 来自 `LOW/MEDIUM/HIGH/PREMIUM`
- [ ] `materials[].brand_recommended` 均为 `false`（禁止品牌）
- [ ] DesignSpec 通过 `design_spec.schema.json` 校验（无额外字段）
- [ ] `design_spec.json` 与 `checkpoint_design_v1.json` 已落盘
- [ ] 返回统一 `Result`（`output_model=DesignSpec`）
- [ ] 不含 CAD / Geometry / Drawing / Layer / Entity / DWG
