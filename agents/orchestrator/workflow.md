# Orchestrator Workflow

## 标准工作流

```
用户输入 → 需求解析 → 方案设计 → 布局规划 → 专业深化 → 综合校验 → 图纸生成 → 导出交付
```

## 详细步骤

1. **需求解析阶段**: 调用 Parser Agent
2. **方案设计阶段**: 调用 Design Agent
3. **布局规划阶段**: 调用 Layout Agent
4. **专业深化阶段**（并行）:
   - Electrical Agent（电气）
   - Plumbing Agent（给排水）
   - Lighting Agent（照明）
   - Ceiling Agent（吊顶）
   - Floor Agent（地面）
   - Elevation Agent（立面）
5. **综合校验阶段**: 调用 Validator + Constraint
6. **图纸生成阶段**: 调用 Drawing Agent
7. **导出交付阶段**: 调用 Export Agent
