"""AnomalyDetectionService — detects anomalous voting patterns.

Implements HU-V09: Detect fanboys and anomalous votes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.user import User
from app.voting.models.user_vote import UserVote
from app.voting.models.vote_event import VoteEvent


class AnomalyDetectionService:
    """Detects anomalous voting patterns."""

    # Thresholds
    SAME_TARGET_THRESHOLD = 0.9  # 90% same target
    RAPID_CHANGE_THRESHOLD = 60  # seconds
    MULTI_ACCOUNT_THRESHOLD = 3  # accounts from same device

    def __init__(self, session: AsyncSession):
        self.session = session

    async def detect_anomalies(self, user_id: str) -> dict:
        """Run all anomaly detection algorithms for a user.

        Args:
            user_id: User ID to check.

        Returns:
            Dict with anomaly detection results.
        """
        results = {
            "user_id": user_id,
            "is_anomalous": False,
            "anomalies": [],
        }

        # Algorithm 1: 90% same-target detection
        same_target = await self._detect_same_target(user_id)
        if same_target["is_anomalous"]:
            results["is_anomalous"] = True
            results["anomalies"].append(same_target)

        # Algorithm 2: Rapid vote changes
        rapid_changes = await self._detect_rapid_changes(user_id)
        if rapid_changes["is_anomalous"]:
            results["is_anomalous"] = True
            results["anomalies"].append(rapid_changes)

        # Algorithm 3: Multi-account detection (requires device fingerprint)
        multi_account = await self._detect_multi_account(user_id)
        if multi_account["is_anomalous"]:
            results["is_anomalous"] = True
            results["anomalies"].append(multi_account)

        # Algorithm 4: Voting pattern analysis
        pattern_anomaly = await self._detect_voting_pattern(user_id)
        if pattern_anomaly["is_anomalous"]:
            results["is_anomalous"] = True
            results["anomalies"].append(pattern_anomaly)

        return results

    async def _detect_same_target(self, user_id: str) -> dict:
        """Detect if user votes for same target in >90% of categories.

        Args:
            user_id: User ID to check.

        Returns:
            Dict with detection result.
        """
        # Get all active votes for user
        result = await self.session.execute(
            select(UserVote).where(UserVote.user_id == user_id)
        )
        votes = result.scalars().all()

        if len(votes) < 5:  # Need minimum votes for meaningful analysis
            return {"algorithm": "same_target", "is_anomalous": False}

        # Count votes per target
        target_counts: dict[str, int] = {}
        for vote in votes:
            target_id = vote.target_id
            target_counts[target_id] = target_counts.get(target_id, 0) + 1

        # Find most common target
        max_count = max(target_counts.values())
        total_votes = len(votes)

        # Check if >90% same target
        ratio = max_count / total_votes
        is_anomalous = ratio > self.SAME_TARGET_THRESHOLD

        return {
            "algorithm": "same_target",
            "is_anomalous": is_anomalous,
            "ratio": ratio,
            "total_votes": total_votes,
            "most_common_count": max_count,
        }

    async def _detect_rapid_changes(self, user_id: str) -> dict:
        """Detect vote changes within <1 minute.

        Args:
            user_id: User ID to check.

        Returns:
            Dict with detection result.
        """
        # Get recent vote changes
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

        result = await self.session.execute(
            select(VoteEvent).where(
                VoteEvent.user_id == user_id,
                VoteEvent.action == "change",
                VoteEvent.created_at >= one_hour_ago,
            ).order_by(VoteEvent.created_at.desc())
        )
        events = result.scalars().all()

        if len(events) < 2:
            return {"algorithm": "rapid_changes", "is_anomalous": False}

        # Check for changes within threshold
        rapid_count = 0
        for i in range(len(events) - 1):
            current = events[i]
            previous = events[i + 1]

            # Ensure both have timezone-aware datetimes
            current_time = current.created_at
            previous_time = previous.created_at

            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=UTC)
            if previous_time.tzinfo is None:
                previous_time = previous_time.replace(tzinfo=UTC)

            time_diff = (current_time - previous_time).total_seconds()

            if time_diff < self.RAPID_CHANGE_THRESHOLD:
                rapid_count += 1

        is_anomalous = rapid_count > 0

        return {
            "algorithm": "rapid_changes",
            "is_anomalous": is_anomalous,
            "rapid_changes_count": rapid_count,
            "total_changes": len(events),
        }

    async def _detect_multi_account(self, user_id: str) -> dict:
        """Detect multiple accounts from same device fingerprint.

        Args:
            user_id: User ID to check.

        Returns:
            Dict with detection result.
        """
        # Get device fingerprints for user
        result = await self.session.execute(
            select(VoteEvent.device_fingerprint).where(
                VoteEvent.user_id == user_id,
                VoteEvent.device_fingerprint.isnot(None),
            ).distinct()
        )
        fingerprints = [row[0] for row in result.all()]

        if not fingerprints:
            return {"algorithm": "multi_account", "is_anomalous": False}

        # Check how many users share these fingerprints
        multi_account_count = 0
        for fingerprint in fingerprints:
            user_count_result = await self.session.execute(
                select(func.count(func.distinct(VoteEvent.user_id))).where(
                    VoteEvent.device_fingerprint == fingerprint
                )
            )
            user_count = user_count_result.scalar() or 0

            if user_count > self.MULTI_ACCOUNT_THRESHOLD:
                multi_account_count += 1

        is_anomalous = multi_account_count > 0

        return {
            "algorithm": "multi_account",
            "is_anomalous": is_anomalous,
            "shared_fingerprints": multi_account_count,
            "total_fingerprints": len(fingerprints),
        }

    async def _detect_voting_pattern(self, user_id: str) -> dict:
        """Detect suspicious voting patterns (e.g., voting at exact intervals).

        Args:
            user_id: User ID to check.

        Returns:
            Dict with detection result.
        """
        # Get recent votes
        one_day_ago = datetime.now(UTC) - timedelta(days=1)

        result = await self.session.execute(
            select(VoteEvent).where(
                VoteEvent.user_id == user_id,
                VoteEvent.created_at >= one_day_ago,
            ).order_by(VoteEvent.created_at.asc())
        )
        events = result.scalars().all()

        if len(events) < 5:
            return {"algorithm": "voting_pattern", "is_anomalous": False}

        # Calculate intervals between votes
        intervals = []
        for i in range(1, len(events)):
            current_time = events[i].created_at
            previous_time = events[i - 1].created_at

            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=UTC)
            if previous_time.tzinfo is None:
                previous_time = previous_time.replace(tzinfo=UTC)

            interval = (current_time - previous_time).total_seconds()
            intervals.append(interval)

        if not intervals:
            return {"algorithm": "voting_pattern", "is_anomalous": False}

        # Check for suspicious patterns
        # 1. Exact same interval (bot-like)
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval > 0:
            variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
            # Low variance means votes are very regular
            is_suspicious = variance < 1.0  # Very low variance
        else:
            is_suspicious = False

        return {
            "algorithm": "voting_pattern",
            "is_anomalous": is_suspicious,
            "avg_interval": avg_interval,
            "vote_count": len(events),
        }

    async def get_user_risk_score(self, user_id: str) -> float:
        """Calculate overall risk score for a user.

        Args:
            user_id: User ID to check.

        Returns:
            Risk score between 0.0 (safe) and 1.0 (high risk).
        """
        anomalies = await self.detect_anomalies(user_id)

        if not anomalies["is_anomalous"]:
            return 0.0

        # Calculate risk based on number and severity of anomalies
        risk = 0.0
        for anomaly in anomalies["anomalies"]:
            if anomaly["algorithm"] == "same_target":
                risk += 0.3 * anomaly.get("ratio", 0)
            elif anomaly["algorithm"] == "rapid_changes":
                risk += 0.2 * min(1.0, anomaly.get("rapid_changes_count", 0) / 5)
            elif anomaly["algorithm"] == "multi_account":
                risk += 0.4 * min(1.0, anomaly.get("shared_fingerprints", 0) / 3)
            elif anomaly["algorithm"] == "voting_pattern":
                risk += 0.1

        return min(1.0, risk)
