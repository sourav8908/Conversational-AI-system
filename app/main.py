import uvicorn
import asyncio
import logging
from app.api.server import app
from app.config.settings import Settings

settings = Settings()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info(f"Starting MCP Server on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "app.api.server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    ) 