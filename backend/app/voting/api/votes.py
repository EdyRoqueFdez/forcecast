"""Vote API routes — FastAPI router for voting operations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware.auth import get_current_user
from app.auth.middleware.turnstile import require_turnstile_vote, verify_turnstile_token
from app.auth.models.user import User
from app.core.feature_flags import get_feature_flags
from app.db.session import get_session
from app.taxonomy.services.core import DomainError
from app.voting.schemas.vote import (
    UserVotesResponse,
    UserVoteItem,
    VoteRequest,
    VoteResponse,
)
from app.voting.services.burst_detection import BurstDetector
from app.voting.services.vote_service import VoteService

router = APIRouter(prefix="/api/v1", tags=["votes"])

# Burst detector singleton
_burst_detector: BurstDetector | None = None


def get_burst_detector() -> BurstDetector:
    """Get or create BurstDetector singleton."""
    global _burst_detector
    if _burst_detector is None:
        # Use dict fallback for now; inject Redis in production
        _burst_detector = BurstDetector(redis_client={})
    return _burst_detector


@router.post("/votes", response_model=VoteResponse, status_code=201)
async def cast_or_change_vote(
    body: VoteRequest,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    turnstile_token: str | None = Depends(require_turnstile_vote),
) -> VoteResponse:
    """Cast a new vote or change an existing vote.

    - If no active vote exists in the category: casts new vote
    - If active vote exists: changes to new target

    CAPTCHA is triggered when:
    - Feature flag is enabled AND
    - User is voting for the first time OR
    - User is voting in burst mode (rapid succession)

    API keys are read-only and cannot vote (403).
    """
    # Block API keys from voting (HU-A09)
    api_key_header = request.headers.get("x-forcecast-api-key") or request.headers.get("X-Forcecast-Api-Key")
    if api_key_header:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403,
            detail="API keys are read-only and cannot vote",
        )

    # Get client info
    ip_address = request.client.host if request.client else None
    device_fingerprint = None  # TODO: extract from request headers

    service = VoteService(db)

    try:
        # Check if user has active vote in category
        existing = await service.user_vote_repo.get(
            user.id, body.category_id, body.target_type
        )

        # Check if CAPTCHA should be enforced
        feature_flags = get_feature_flags()
        captcha_enabled = await feature_flags.is_enabled("FEATURE_CAPTCHA_VOTE")

        if captcha_enabled:
            # Check if this is first vote or burst
            is_first_vote = await service.is_first_vote(user.id)
            burst_detector = get_burst_detector()
            is_burst = await burst_detector.is_burst(user.id)

            if is_first_vote or is_burst:
                # Token must have been verified by middleware
                if not turnstile_token:
                    from fastapi import HTTPException

                    raise HTTPException(
                        status_code=403,
                        detail="CAPTCHA required for this vote",
                    )

        if existing:
            # Change vote
            result = await service.change_vote(
                user=user,
                target_type=body.target_type,
                target_id=body.target_id,
                category_id=body.category_id,
                idempotency_key=body.idempotency_key,
                comment=body.comment,
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
                comment=body.comment,
                request_id=request.headers.get("X-Request-ID"),
                ip_address=ip_address,
                device_fingerprint=device_fingerprint,
            )

        # Record vote for burst detection
        burst_detector = get_burst_detector()
        await burst_detector.record_vote(user.id)

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
    """Revoke an active vote in a category.

    API keys are read-only and cannot revoke votes (403).
    """
    # Block API keys from voting (HU-A09)
    api_key_header = request.headers.get("x-forcecast-api-key") or request.headers.get("X-Forcecast-Api-Key")
    if api_key_header:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403,
            detail="API keys are read-only and cannot vote",
        )

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


# --- HU-V08: Report abusive vote/comment ---


class ReportRequest(BaseModel):
    """Request body for reporting a vote or comment."""

    target_id: str
    target_type: str  # "vote" or "comment"
    reason: str  # "spam", "offensive", "false", "duplicate", "other"
    details: str | None = None


class ReportResponse(BaseModel):
    """Response for report submission."""

    report_id: str
    status: str
    message: str


from pydantic import BaseModel


@router.post("/votes/report", response_model=ReportResponse, status_code=201)
async def report_vote_or_comment(
    body: ReportRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ReportResponse:
    """HU-V08 — Report an abusive vote or comment.

    - target_type: "vote" or "comment"
    - reason: "spam", "offensive", "false", "duplicate", "other"
    - Creates Report with status `pending`
    """
    import uuid

    # Validate reason
    valid_reasons = {"spam", "offensive", "false", "duplicate", "other"}
    if body.reason not in valid_reasons:
        raise HTTPException(status_code=422, detail=f"Invalid reason. Must be one of: {', '.join(valid_reasons)}")

    # Create report
    report_id = str(uuid.uuid4())
    from app.voting.models.report import Report
    from datetime import datetime

    report = Report(
        id=report_id,
        target_id=body.target_id,
        target_type=body.target_type,
        reporter_id=user.id,
        reason=body.reason,
        details=body.details,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(report)
    await db.commit()

    return ReportResponse(
        report_id=report_id,
        status="pending",
        message="Report submitted. An administrator will review it.",
    )


class ReportItem(BaseModel):
    """Single report item for admin review."""

    report_id: str
    target_id: str
    target_type: str
    reporter_id: str
    reason: str
    details: str | None
    status: str
    created_at: str


class AdminReportsResponse(BaseModel):
    """Response for admin reports list."""

    reports: list[ReportItem]
    total: int


class ReportActionRequest(BaseModel):
    """Request body for approving/rejecting a report."""

    action: str  # "approve" or "reject"
    admin_notes: str | None = None


@router.get("/admin/votes/reports", response_model=AdminReportsResponse)
async def get_reports(
    status: str = Query("pending", description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> AdminReportsResponse:
    """HU-V08 — Get reports for admin review (admin only)."""
    # TODO: Check if user is admin
    from app.voting.models.report import Report
    from sqlalchemy import select, func

    # Get reports
    query = select(Report).where(Report.status == status).order_by(Report.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    reports = result.scalars().all()

    # Get total count
    count_query = select(func.count(Report.id)).where(Report.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return AdminReportsResponse(
        reports=[
            ReportItem(
                report_id=r.id,
                target_id=r.target_id,
                target_type=r.target_type,
                reporter_id=r.reporter_id,
                reason=r.reason,
                details=r.details,
                status=r.status,
                created_at=r.created_at.isoformat(),
            )
            for r in reports
        ],
        total=total,
    )


@router.put("/admin/votes/reports/{report_id}")
async def review_report(
    report_id: str,
    body: ReportActionRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """HU-V08 — Approve or reject a report (admin only)."""
    # TODO: Check if user is admin
    from app.voting.models.report import Report
    from datetime import datetime

    # Validate action
    if body.action not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail="Action must be 'approve' or 'reject'")

    # Get report
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Update report
    report.status = body.action + "d"  # "approved" or "rejected"
    report.reviewed_by = user.id
    report.reviewed_at = datetime.utcnow()
    await db.commit()

    return {"status": report.status, "message": f"Report {report.status}"}


# Need to import select for admin endpoints
from sqlalchemy import select


# --- HU-V10: Vote history ---


class VoteHistoryItem(BaseModel):
    """Single vote history item."""

    event_id: str
    event_type: str  # "cast", "change", "revoke"
    target_id: str
    previous_target_id: str | None
    category_id: str
    target_type: str
    comment: str | None
    created_at: str


class VoteHistoryResponse(BaseModel):
    """Response for vote history."""

    events: list[VoteHistoryItem]
    total: int
    has_more: bool
    next_cursor: str | None


@router.get("/me/votes/history", response_model=VoteHistoryResponse)
async def get_vote_history(
    request: Request,
    response: Response,
    category_id: str | None = Query(None, description="Filter by category"),
    target_type: str | None = Query(None, description="Filter by target type"),
    event_type: str | None = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> VoteHistoryResponse:
    """HU-V10 — Get vote history for the authenticated user.

    - Returns VoteEvent with timestamp, type, previous target, new target, category, comment
    - Filter by category, target, date, type
    - Paginated results
    """
    from app.voting.models.vote_event import VoteEvent
    from sqlalchemy import select, func

    # Build query
    query = select(VoteEvent).where(VoteEvent.user_id == user.id)

    # Apply filters
    if category_id:
        query = query.where(VoteEvent.category_id == category_id)
    if target_type:
        query = query.where(VoteEvent.target_type == target_type)
    if event_type:
        query = query.where(VoteEvent.event_type == event_type)

    # Order by created_at descending
    query = query.order_by(VoteEvent.created_at.desc())

    # Get total count
    count_query = select(func.count(VoteEvent.id)).where(VoteEvent.user_id == user.id)
    if category_id:
        count_query = count_query.where(VoteEvent.category_id == category_id)
    if target_type:
        count_query = count_query.where(VoteEvent.target_type == target_type)
    if event_type:
        count_query = count_query.where(VoteEvent.event_type == event_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()

    # Build response
    has_more = offset + limit < total
    next_cursor = None
    if has_more and events:
        next_cursor = str(offset + limit)

    return VoteHistoryResponse(
        events=[
            VoteHistoryItem(
                event_id=e.id,
                event_type=e.event_type,
                target_id=e.target_id,
                previous_target_id=e.previous_target_id,
                category_id=e.category_id,
                target_type=e.target_type,
                comment=e.comment,
                created_at=e.created_at.isoformat(),
            )
            for e in events
        ],
        total=total,
        has_more=has_more,
        next_cursor=next_cursor,
    )


# --- HU-V11: Public votes of other users ---


class PublicVoteItem(BaseModel):
    """Single public vote item."""

    category_id: str
    target_type: str
    target_id: str
    comment: str | None
    created_at: str


class PublicVotesResponse(BaseModel):
    """Response for public votes."""

    username: str
    votes: list[PublicVoteItem]
    total: int


@router.get("/users/{username}/votes", response_model=PublicVotesResponse)
async def get_public_votes(
    username: str,
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
) -> PublicVotesResponse:
    """HU-V11 — Get public votes for another user.

    - Only shows votes if target profile is public
    - No private data exposed (email, IP, device)
    - Respects privacy settings
    """
    from app.users.models.user import User
    from app.voting.models.vote_event import UserVote
    from sqlalchemy import select, func

    # Get user by username
    user_result = await db.execute(
        select(User).where(User.username == username)
    )
    target_user = user_result.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if profile is public
    if hasattr(target_user, "profile_visibility") and target_user.profile_visibility != "public":
        return PublicVotesResponse(
            username=username,
            votes=[],
            total=0,
        )

    # Get public votes
    query = select(UserVote).where(
        UserVote.user_id == target_user.id,
        UserVote.is_active == True,
    ).order_by(UserVote.created_at.desc())

    # Get total count
    count_query = select(func.count(UserVote.id)).where(
        UserVote.user_id == target_user.id,
        UserVote.is_active == True,
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    votes = result.scalars().all()

    return PublicVotesResponse(
        username=username,
        votes=[
            PublicVoteItem(
                category_id=v.category_id,
                target_type=v.target_type,
                target_id=v.target_id,
                comment=v.comment,
                created_at=v.created_at.isoformat(),
            )
            for v in votes
        ],
        total=total,
    )
