"""Voting enums — VoteAction, TargetType."""

from enum import Enum


class StrEnum(str, Enum):
    """Base for string enums with value-direct str() representation."""

    def __str__(self) -> str:
        return str(self.value)


class VoteAction(StrEnum):
    """Vote action types."""
    VOTE = "vote"
    CHANGE = "change"
    REVOKE = "revoke"


class TargetType(StrEnum):
    """Vote target types."""
    MODEL = "model"
    ORCHESTRATOR = "orchestrator"
