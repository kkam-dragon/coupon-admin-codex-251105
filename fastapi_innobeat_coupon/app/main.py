from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.core.scheduler import shutdown_scheduler, start_scheduler

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # ⭐ 모든 Origin 허용
    allow_credentials=True,
    allow_methods=["*"],     # ⭐ 모든 HTTP 메서드 허용 (GET/POST/PUT 등)
    allow_headers=["*"],     # ⭐ 모든 헤더 허용
)

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
