# 示例输入数据（Phase 3）

供 Parser Agent 单元测试 / 演示使用。

| 目录 | 内容 | 说明 |
| --- | --- | --- |
| `empty_project/` | `empty.txt`（0 字节） | 空输入场景（测试加载/大小/Hash） |
| `sample_json/` | `sample.json` | 合法 OriginalModel JSON，Parser 会将其几何作为提示填充 |
| `sample_image/` | `sample.png` | 占位图片（1x1 PNG），识别为 IMAGE |
| `sample_pdf/` | `sample.pdf` | 占位 PDF，识别为 PDF |
| `sample_dwg_placeholder/` | `sample.dwg` | DWG 占位文件（当前阶段无 AutoCAD，识别为 DWG） |

注：DWG 暂使用占位文件，Phase 3 不接入 AutoCAD MCP（见 PHASE 规则 §15）。
