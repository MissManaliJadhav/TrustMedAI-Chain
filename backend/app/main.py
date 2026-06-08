from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import Base, engine, SessionLocal
from app.services.bootstrap import ensure_bootstrap_data
from app.services.schema import ensure_runtime_schema


app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    description="Trustworthy explainable AI, dynamic trust evolution, blockchain auditability, and federated healthcare diagnosis.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine)
    db = SessionLocal()
    try:
        ensure_bootstrap_data(db)
    finally:
        db.close()


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.project_name}
