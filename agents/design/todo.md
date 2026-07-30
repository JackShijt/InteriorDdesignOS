# Design Agent · TODO（已完成 / 范围外）

## 已完成（Phase 4 v1.0）
- [x] DesignSpec Schema（`schemas/design/design_spec.schema.json`）
- [x] Requirement Parser / Constraint Parser / Style / Budget / Family / Material Planner
- [x] DesignSpec 组装 + Schema 校验
- [x] Workspace 自动保存（`design_spec.json` v1）+ Checkpoint（`checkpoint_design_v1.json`）
- [x] Dispatcher 集成（Parser → Design）
- [x] Pipeline 新增 `DESIGN_SPEC` 阶段，完成后停止
- [x] CLI `python main.py design`
- [x] 测试：`tests/design/*` + `tests/e2e` 通过

## 范围外（§17 禁止，留给后续阶段）
- [ ] Layout Agent（设计决策下游消费者）
- [ ] Geometry / Drawing / DWG / AutoCAD / 家具摆放 / 墙体生成 / 尺寸计算
- [ ] LLM 增强（当前为确定性规则解析）
