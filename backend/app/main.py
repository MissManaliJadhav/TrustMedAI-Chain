import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import Base, engine, SessionLocal
from app.services.bootstrap import ensure_bootstrap_data
from app.services.schema import ensure_runtime_schema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment.lower() == "production":
        if settings.jwt_secret_key == "replace-with-a-long-random-secret":
            raise RuntimeError("JWT_SECRET_KEY must be changed in production")
        if settings.super_admin_password == "ChangeMe123!":
            raise RuntimeError("SUPER_ADMIN_PASSWORD must be changed in production")
    logger.info("Starting TrustMedAI backend and initializing runtime schema")
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine)
    db = SessionLocal()
    try:
        ensure_bootstrap_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    description="Trustworthy explainable AI, dynamic trust evolution, blockchain auditability, and federated healthcare diagnosis.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.project_name}
