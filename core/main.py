"""
Harness Engine — 入口。
启动引擎服务：python core/main.py
"""

import sys
from pathlib import Path

# 支持 `python core/main.py` 直接运行：
# 把项目根目录（而非 core/）加入导入路径，使 `from core.xxx import ...` 可用
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "core.server:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )
