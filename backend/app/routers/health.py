from __future__ import annotations

from fastapi import APIRouter

from .. import database
from ..config import VERSION
from ..services import qdrant_vector_store
from ..services.workflow import describe_workflow

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict:
    database.init_db()
    qdrant_status = "qdrant-ready" if qdrant_vector_store.is_available() else "sqlite-fallback-ready"
    return {"status": "ok", "version": VERSION, "vector_store_status": qdrant_status, "database_status": "ok", "workflow": describe_workflow()}
