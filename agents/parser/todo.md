# Parser Agent - TODO

## 已完成（Phase 3 · v1.0）
- [x] 输入类型识别（InputType：DWG/DXF/PDF/IMAGE/TEXT/ZIP/UNKNOWN）
- [x] Input Loader（存在性 / 大小 / sha256 Hash / MIME）
- [x] Normalizer（统一 InputContext）
- [x] OriginalModel Builder（6 必填字段，几何可空数组，禁止 null）
- [x] Schema 校验（original_model.schema.json，失败即中止）
- [x] Workspace 落盘（original_model.json v1）
- [x] Checkpoint 落盘（checkpoint_parser_v1.json）
- [x] Dispatcher / Orchestrator 集成
- [x] 统一 Result（success/output_model/messages/quality/next_tasks=["design"]）
- [x] ISO8601 统一日志
- [x] 异常体系（RecoverableError / ValidationError / FatalError）
- [x] 单元测试（tests/parser，含正常/空/错误/不合法/不存在文件）
- [x] 示例数据（examples/input/）
- [x] scripts/demo_parser.py 端到端验证

## 后续（非 Phase 3 范围）
- [ ] 真实 DWG/DXF 几何提取（需 CAD 解析能力，受 §15 限制，待后续阶段）
- [ ] 真实 PDF / 图片 OCR 识别
- [ ] 质量评估升级（从占位评分到几何完整度评估）
