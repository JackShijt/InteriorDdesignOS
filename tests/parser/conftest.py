"""Parser 单元测试公共配置：将仓库根加入 import 路径。"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
