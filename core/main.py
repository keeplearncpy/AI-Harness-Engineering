"""
Harness Engine — Entry Point.
Start the engine server: python core/main.py
"""

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
