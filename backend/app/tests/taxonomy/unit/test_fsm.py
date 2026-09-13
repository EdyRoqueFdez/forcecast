"""Unit tests for Status FSM — RED phase.

Covers Task 1.3: Status FSM (R4)
Specs: ModelStatus transitions draft→pending_review→approved/rejected, approved→deprecated
      ProviderStatus, CategoryStatus transitions
"""
import pytest


def test_model_status_valid_transitions():
    from app.taxonomy.models.enums import ModelStatus
    from app.taxonomy.services.core import validate_status_transition

    assert validate_status_transition(ModelStatus.DRAFT, ModelStatus.PENDING_REVIEW) is True
    assert validate_status_transition(ModelStatus.PENDING_REVIEW, ModelStatus.APPROVED) is True
    assert validate_status_transition(ModelStatus.PENDING_REVIEW, ModelStatus.REJECTED) is True
    assert validate_status_transition(ModelStatus.APPROVED, ModelStatus.DEPRECATED) is True


def test_model_status_valid_transitions_string_input():
    from app.taxonomy.services.core import validate_status_transition

    # also accept raw strings
    assert validate_status_transition("draft", "pending_review") is True
    assert validate_status_transition("pending_review", "approved") is True


def test_model_status_invalid_transitions_raise_409():
    from app.taxonomy.models.enums import ModelStatus
    from app.taxonomy.services.core import validate_status_transition, DomainError

    invalid_pairs = [
        (ModelStatus.DRAFT, ModelStatus.APPROVED),
        (ModelStatus.DRAFT, ModelStatus.REJECTED),
        (ModelStatus.DRAFT, ModelStatus.DEPRECATED),
        (ModelStatus.DRAFT, ModelStatus.DRAFT),
        (ModelStatus.PENDING_REVIEW, ModelStatus.DRAFT),
        (ModelStatus.PENDING_REVIEW, ModelStatus.DEPRECATED),
        (ModelStatus.APPROVED, ModelStatus.REJECTED),
        (ModelStatus.APPROVED, ModelStatus.PENDING_REVIEW),
        (ModelStatus.APPROVED, ModelStatus.DRAFT),
        (ModelStatus.REJECTED, ModelStatus.APPROVED),
        (ModelStatus.REJECTED, ModelStatus.DEPRECATED),
        (ModelStatus.DEPRECATED, ModelStatus.APPROVED),
    ]
    for current, target in invalid_pairs:
        with pytest.raises(DomainError) as exc:
            validate_status_transition(current, target)
        assert exc.value.status_code == 409
        assert "409" in str(exc.value) or exc.value.status_code == 409


def test_model_status_invalid_direct_approve_from_draft():
    from app.taxonomy.models.enums import ModelStatus
    from app.taxonomy.services.core import validate_status_transition, DomainError

    with pytest.raises(DomainError) as exc:
        validate_status_transition(ModelStatus.DRAFT, ModelStatus.APPROVED)
    assert exc.value.status_code == 409


def test_provider_status_valid_transitions():
    from app.taxonomy.models.enums import ProviderStatus
    from app.taxonomy.services.core import validate_provider_status_transition

    assert validate_provider_status_transition(ProviderStatus.ACTIVE, ProviderStatus.DEPRECATED) is True
    assert validate_provider_status_transition(ProviderStatus.ACTIVE, ProviderStatus.BANNED) is True
    assert validate_provider_status_transition(ProviderStatus.DEPRECATED, ProviderStatus.BANNED) is True


def test_provider_status_invalid_transitions():
    from app.taxonomy.models.enums import ProviderStatus
    from app.taxonomy.services.core import validate_provider_status_transition, DomainError

    invalid = [
        (ProviderStatus.DEPRECATED, ProviderStatus.ACTIVE),
        (ProviderStatus.BANNED, ProviderStatus.ACTIVE),
        (ProviderStatus.BANNED, ProviderStatus.DEPRECATED),
        (ProviderStatus.ACTIVE, ProviderStatus.ACTIVE),
    ]
    for cur, tgt in invalid:
        with pytest.raises(DomainError) as exc:
            validate_provider_status_transition(cur, tgt)
        assert exc.value.status_code == 409


def test_category_status_valid():
    from app.taxonomy.models.enums import CategoryStatus
    from app.taxonomy.services.core import validate_category_status_transition

    assert validate_category_status_transition(CategoryStatus.ACTIVE, CategoryStatus.DEPRECATED) is True


def test_category_status_invalid():
    from app.taxonomy.models.enums import CategoryStatus
    from app.taxonomy.services.core import validate_category_status_transition, DomainError

    with pytest.raises(DomainError):
        validate_category_status_transition(CategoryStatus.DEPRECATED, CategoryStatus.ACTIVE)
    with pytest.raises(DomainError):
        validate_category_status_transition(CategoryStatus.ACTIVE, CategoryStatus.ACTIVE)


def test_can_transition_helper():
    from app.taxonomy.models.enums import ModelStatus
    from app.taxonomy.services.core import can_transition

    assert can_transition(ModelStatus.DRAFT, ModelStatus.PENDING_REVIEW) is True
    assert can_transition(ModelStatus.DRAFT, ModelStatus.APPROVED) is False
    assert can_transition("approved", "deprecated") is True
    assert can_transition("rejected", "approved") is False
