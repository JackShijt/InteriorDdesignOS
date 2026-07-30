# Parser Agent - Schema

## 数据契约
输入输出遵循 `schemas/` 定义：
- 输出模型：`schemas/original_model.schema.json`（含相对 `$ref` 至 `schemas/metadata.schema.json`）。
- 校验库：`jsonschema` + `referencing`（Draft 2020-12）。

## OriginalModel 必填顶层键（6 个，禁止 null）
| 键 | 类型 | 说明 |
| --- | --- | --- |
| `metadata` | object | 项目 / 任务 / Agent / 时间 / 质量 |
| `units` | object | 长度 / 面积 / 角度单位（mm / m² / °） |
| `coordinates` | object | 坐标系 / 原点 / 单位 |
| `walls` | array | 墙体；不可解析时为空数组 `[]` |
| `doors` | array | 门；不可解析时为空数组 `[]` |
| `windows` | array | 窗；不可解析时为空数组 `[]` |
| `rooms` | array | 房间；不可解析时为空数组 `[]` |

> 顶层 `additionalProperties` 为 `true`（允许扩展字段），但 6 个必填键缺失或嵌套非法将被校验捕获。

## 字段约定
- 坐标单位：毫米 (mm)
- 面积单位：平方米 (m²)
- 字段命名：snake_case
- 角度单位：度 (°)

## 校验失败处理
抛 `ValidationError`，流程立即中止，**不写 Workspace / Checkpoint**（除非已在此前步骤落盘）。
