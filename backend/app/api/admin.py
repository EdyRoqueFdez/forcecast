"""Admin API — protected by require_admin. Taxonomy admin endpoints."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.middleware.auth import require_admin
from app.auth.models.user import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class IngestionRunRequest(BaseModel):
    source: str = Field(..., min_length=1, description="Ingestion source slug")


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[str]
    secret: Optional[str] = None


class TaxonomyVersionCreate(BaseModel):
    version: str
    notes: Optional[str] = None


@router.post("/models/{id}/approve")
async def approve_model(id: str, current_user: User = Depends(require_admin)):
    """Approve a pending model — stub returns approved status."""
    # Validate UUID
    try:
        uuid.UUID(id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid model id")
    # In MVP without DB taxonomy, return stub success
    # If taxonomy tables existed, we'd check ModelHosting etc.
    return {"id": id, "status": "approved", "approved_by": str(current_user.id)}


@router.post("/models/{id}/reject")
async def reject_model(id: str, payload: dict, current_user: User = Depends(require_admin)):
    try:
        uuid.UUID(id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid model id")
    reason = payload.get("reason", "") if isinstance(payload, dict) else ""
    return {"id": id, "status": "rejected", "reason": reason, "rejected_by": str(current_user.id)}


@router.post("/ingestion/run")
async def trigger_ingestion(payload: IngestionRunRequest, current_user: User = Depends(require_admin)):
    # Validate source against allowed list from seeds/ingestion_sources if available
    # For MVP, accept openrouter and mock sources
    allowed = {"openrouter", "huggingface", "mock"}
    if payload.source not in allowed:
        # also check seeds file? Try to load dynamic but fallback to allowed
        raise HTTPException(status_code=422, detail=f"Invalid source: {payload.source}")
    run_id = str(uuid.uuid4())
    return {"id": run_id, "source": payload.source, "status": "running", "triggered_by": str(current_user.id)}


@router.post("/taxonomy/versions")
async def create_taxonomy_version(payload: TaxonomyVersionCreate, current_user: User = Depends(require_admin)):
    version_id = str(uuid.uuid4())
    return {"id": version_id, "version": payload.version, "notes": payload.notes, "is_current": False}


@router.post("/taxonomy/versions/{id}/activate")
async def activate_taxonomy_version(id: str, current_user: User = Depends(require_admin)):
    try:
        uuid.UUID(id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid version id")
    return {"id": id, "is_current": True, "activated_by": str(current_user.id)}


@router.post("/webhooks")
async def register_webhook(payload: WebhookCreateRequest, current_user: User = Depends(require_admin)):
    webhook_id = str(uuid.uuid4())
    return {"id": webhook_id, "url": payload.url, "events": payload.events, "is_active": True}


# Additional webhook list for completeness
@router.get("/webhooks")
async def list_webhooks(current_user: User = Depends(require_admin)):
    return {"data": [], "total": 0}
