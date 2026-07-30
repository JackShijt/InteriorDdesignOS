# Design Agent · Memory（记忆）

Design Agent 为**无状态确定性 Agent**（Phase 4 v1.0）：每次运行仅依赖当次传入的
`OriginalModel + requirement`，不产生跨项目长期记忆。

运行期状态通过统一机制落盘：
- `workspace/projects/<project_id>/design_spec.json`（设计决策结果）
- `workspace/projects/<project_id>/checkpoint_design_v1.json`（检查点，供恢复）
- `workspace/logs/`（统一日志，由 `UnifiedLogger` 写入）

恢复：Pipeline `resume_project()` 读取上述文件重建 Project / TaskGraph / Stage / Context。
