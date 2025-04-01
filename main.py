from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from src.db.models import create_tables
from src.db.depends import db
from src.services.redis_cache import cache
from src.services.blockchain import bittensor_service
from src.api.routes import dividends
from src.core.security import get_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events for database, cache, and blockchain connections.
    """

    await create_tables()
    if not db.is_connected:
        await db.connect()

    yield 
    
    if db.is_connected:
        await db.disconnect()
    await cache.close()
    await bittensor_service.close()


app = FastAPI(
    title="Bittensor TAO Dividends API",
    description="Async API for querying TAO dividends and automated sentiment-based staking",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    dividends.router,
    prefix="/api/v1",
    tags=["Dividends"],
    dependencies=[Depends(get_api_key)]
)


@app.get("/")
async def root():
    return {"message": "Welcome to Bittensor TAO Dividends API"}

@app.get("/health/", tags=["Health Check"])
async def health_check():
    """
    Comprehensive health check endpoint that verifies all services.
    """
    health_status = {
        "status": "ok",
        "services": {
            "database": {"status": "unknown"},
            "redis": {"status": "unknown"},
            "bittensor": {"status": "unknown"}
        }
    }
    
    # Redis health
    try:
        redis_health, redis_error = await cache.health_check()
        health_status["services"]["redis"] = {
            "status": "ok" if redis_health else "error",
            "error": redis_error if not redis_health else None
        }
        if not redis_health:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["redis"] = {"status": "error", "error": str(e)}
        health_status["status"] = "degraded"
    
    # DB health
    try:
        if db.is_connected:
            health_status["services"]["database"] = {"status": "ok"}
        else:
            health_status["services"]["database"] = {"status": "error", "error": "Not connected"}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["database"] = {"status": "error", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Bittensor service health
    try:
        subtensor = await bittensor_service._get_subtensor()
        if subtensor:
            health_status["services"]["bittensor"] = {"status": "ok"}
        else:
            health_status["services"]["bittensor"] = {"status": "error", "error": "Not initialized"}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["bittensor"] = {"status": "error", "error": str(e)}
        health_status["status"] = "degraded"
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)