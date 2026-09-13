"""Vote API routes — FastAPI router for voting operations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware.auth import get_current_user
from app.auth.models.user import User
from app.db.session import get_session
from app.taxonomy.services.core import DomainError
from app.voting.schemas.vote import (
    UserVotesResponse,
    UserVoteItem,
    VoteRequest,
    VoteResponse,
)
from app.voting.services.vote_service import VoteService

router = APIRouter(prefix="/api/v1", tags=["votes"])


@router.post("/votes", response_model=VoteResponse, status_code=201)
async def cast_or_change_vote(
    body: VoteRequest,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> VoteResponse:
    """Cast a new vote or change an existing vote.

    - If no active vote exists in the category: casts new vote
    - If active vote exists: changes to new target
    """
    # Get client info
    ip_address = request.client.host if request.client else None
    device_fingerprint = None  # TODO: extract from request headers

    service = VoteService(db)

    try:
        # Check if user has active vote in category
        existing = await service.user_vote_repo.get(
            user.id, body.category_id, body.target_type
        )

        if existing:
            # Change vote
            result = await service.change_vote(
                user=user,
                target_type=body.target_type,
                target_id=body.target_id,
                category_id=body.category_id,
                idempotency_key=body.idempotency_key,
                request_id=request.headers.get("X-Request-ID"),
                ip_address=ip_address,
                device_fingerprint=device_fingerprint,
            )
        else:
            # Cast new vote
            result = await service.cast_vote(
                user=user,
                target_type=body.target_type,
                target_id=body.target_id,
                category_id=body.category_id,
                idempotency_key=body.idempotency_key,
                request_id=request.headers.get("X-Request-ID"),
                ip_address=ip_address,
                device_fingerprint=device_fingerprint,
            )

        return VoteResponse(**result)

    except DomainError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete(
    "/votes/{category_id}",
    response_model=VoteResponse,
)
async def revoke_vote(
    category_id: str,
    request: Request,
    response: Response,
    target_type: str = "model",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> VoteResponse:
    """Revoke an active vote in a category."""
    import uuid

    ip_address = request.client.host if request.client else None
    device_fingerprint = None

    service = VoteService(db)

    try:
        result = await service.revoke_vote(
            user=user,
            target_type=target_type,
            category_id=category_id,
            idempotency_key=str(uuid.uuid4()),
            request_id=request.headers.get("X-Request-ID"),
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
        )

        return VoteResponse(**result)

    except DomainError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/users/me/votes", response_model=UserVotesResponse)
async def get_my_votes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> UserVotesResponse:
    """Get all active votes for the authenticated user."""
    service = VoteService(db)
    votes = await service.get_user_votes(user)

    return UserVotesResponse(
        votes=[
            UserVoteItem(
                category_id=v["category_id"],
                target_type=v["target_type"],
                target_id=v["target_id"],
                weight=v["weight"],
                created_at=v["created_at"],
                updated_at=v["updated_at"],
            )
            for v in votes
        ]
    )
