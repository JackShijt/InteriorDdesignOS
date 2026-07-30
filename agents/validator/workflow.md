# Validator Agent - Workflow

## 工作流定位
本代理处于 InteriorDesignOS 流水线中，由 Orchestrator 调度执行。

## 标准步骤
1. 接收 Orchestrator 分发的任务与上下文（见 input.md）
2. 解析输入数据
3. 执行专业计算 / 设计逻辑
4. 生成结构化输出（见 output.md）
5. 按 checklist.md 自检
6. 将结果返回 Orchestrator
