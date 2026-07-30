# Parser Agent - Input

## 输入来源
由 Orchestrator / Dispatcher 经任务上下文传入（`AgentContext`）。

## 取值顺序
1. `context.input_refs[0]` —— 输入文件绝对路径（优先）。
2. `context.parameters["input_path"]` —— 备用。
3. 二者皆空 → 抛 `FatalError`（"Parser 缺少输入"）。

## 支持类型
| 扩展名 | InputType | 说明 |
| --- | --- | --- |
| `.dwg` | DWG | 占位解析，几何置空 |
| `.dxf` | DXF | 占位解析，几何置空 |
| `.pdf` | PDF | 占位解析，几何置空 |
| `.png` / `.jpg` / `.jpeg` | IMAGE | 占位解析，几何置空 |
| `.json` | TEXT | 若内容合法 OriginalModel，则采纳其中几何作为 hints |
| `.txt` | TEXT | 纯文本 / 用户需求，几何置空 |
| `.zip` | ZIP | 占位解析，几何置空 |
| 其他 | UNKNOWN | 魔数兜底猜测，仍失败则 UNKNOWN，置信度最低 |

## 加载内容（不做业务解析）
- 存在性、文件大小（bytes）、sha256 `file_hash`、MIME 类型。
