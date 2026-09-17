from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.config import get_settings
from app.api.routes_query import router as query_router
from app.api.routes_anomalies import router as anomalies_router
from app.api.routes_health import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered customer support ticket analysis system",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(query_router, prefix="/api", tags=["query"])
app.include_router(anomalies_router, prefix="/api", tags=["anomalies"])


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "query": "/api/query",
        "anomalies": "/api/anomalies",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)