from fastapi import FastAPI

from app.api.routes import api_router
from app.core.config import settings
from app.core.scheduler import shutdown_scheduler, start_scheduler

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(api_router)


@app.on_event("startup")
def _startup() -> None:
    start_scheduler()


@app.on_event("shutdown")
def _shutdown() -> None:
    shutdown_scheduler()

@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    return {"message": f"{settings.app_name} ready"}
