# Design Agent（Phase 4 v1.0）

InteriorDesignOS 第一个具备 AI 决策能力的 Agent。

> 把 **用户需求 + OriginalModel** 固化为统一的 **DesignSpec** —— 系统所有设计决策的唯一来源（SSOT），供下游 Layout Agent 使用。

**不负责**：CAD / 几何 / 布局 / 绘图（见 §17 禁止项）。

## 输入
- `OriginalModel`（`workspace/projects/<project_id>/original_model.json`，由 Parser 产出）
- 用户自然语言需求（`requirement`，经 Pipeline / CLI 传入）

## 输出
- `DesignSpec`（`workspace/projects/<project_id>/design_spec.json`，v1）
- `checkpoint_design_v1.json`
- 统一 `Result`（success / output_model=DesignSpec / quality）

## 目录
| 文件 | 职责 |
|------|------|
| `design.py` | 主入口：组装 → 校验 → 落盘 → 返回 Result（框架安全） |
| `requirement_parser.py` | 用户需求 → `UserRequirement` |
| `constraint_parser.py` | OriginalModel → `ConstraintSet` |
| `style_planner.py` | 风格规划（§5，允许多标签） |
| `budget_planner.py` | 预算等级 + 分配建议（§6） |
| `family_analyzer.py` | 家庭画像（§7） |
| `material_planner.py` | 材料偏好（§8，禁止品牌） |
| `validator.py` | 按 `schemas/design/design_spec.schema.json` 校验 |
| `result_builder.py` | 构造统一 `Result` |
| `exceptions.py` | 异常（复用统一 error_handler） |

## 运行方式
```bash
# 经 Pipeline 全流程（Parser → Design）
python main.py run <project_id> --input <original_model.json> --requirement "<text>"

# 直接运行 Design Agent（需已有 OriginalModel）
python main.py design <project_id> --input <original_model.json> --requirement "<text>"

# 编程方式
from agents.design.design import DesignAgent
DesignAgent().generate(original_model, requirement, project_id, task_id)
```

## 流程
`UserRequirement + ConstraintSet` → Style / Budget / Family / Material Planner →
组装 DesignSpec → Schema 校验 → 落盘 Workspace + Checkpoint → Result。

## 约束
- DesignSpec 禁止包含 CAD / Geometry / Drawing / Layer / Entity / DWG（schema `additionalProperties:false` 强制）。
- 确定性规则解析（无 LLM 依赖），可测试、可复现。
