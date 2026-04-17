"""Unit tests for session domain logic — T021.

Tests are written FIRST per TDD mandate. They must FAIL before implementation.
"""
from __future__ import annotations

import pytest

from glucotrack.domain.session import InsufficientEntriesError, SessionStateMachine
from glucotrack.models.session import SessionStatus


class TestSessionStateMachine:
    """Tests for session state transitions and business rules."""

    def test_can_complete_requires_food_and_cgm(self) -> None:
        sm = SessionStateMachine()
        assert sm.can_complete(food_count=1, cgm_count=1) is True

    def test_cannot_complete_without_food(self) -> None:
        sm = SessionStateMachine()
        assert sm.can_complete(food_count=0, cgm_count=1) is False

    def test_cannot_complete_without_cgm(self) -> None:
        sm = SessionStateMachine()
        assert sm.can_complete(food_count=1, cgm_count=0) is False

    def test_cannot_complete_both_missing(self) -> None:
        sm = SessionStateMachine()
        assert sm.can_complete(food_count=0, cgm_count=0) is False

    def test_can_complete_with_multiple_entries(self) -> None:
        sm = SessionStateMachine()
        assert sm.can_complete(food_count=3, cgm_count=4) is True

    def test_validate_completion_raises_when_insufficient(self) -> None:
        sm = SessionStateMachine()
        with pytest.raises(InsufficientEntriesError):
            sm.validate_completion(food_count=0, cgm_count=1)

    def test_validate_completion_passes_when_sufficient(self) -> None:
        sm = SessionStateMachine()
        sm.validate_completion(food_count=1, cgm_count=1)  # no exception

    def test_open_to_completed_is_valid(self) -> None:
        sm = SessionStateMachine()
        result = sm.transition(SessionStatus.OPEN, "complete")
        assert result == SessionStatus.COMPLETED

    def test_open_to_expired_is_valid(self) -> None:
        sm = SessionStateMachine()
        result = sm.transition(SessionStatus.OPEN, "expire")
        assert result == SessionStatus.EXPIRED

    def test_completed_to_analysed_is_valid(self) -> None:
        sm = SessionStateMachine()
        result = sm.transition(SessionStatus.COMPLETED, "analyse")
        assert result == SessionStatus.ANALYSED

    def test_analysed_is_terminal(self) -> None:
        sm = SessionStateMachine()
        with pytest.raises(ValueError):
            sm.transition(SessionStatus.ANALYSED, "complete")

    def test_expired_is_terminal(self) -> None:
        sm = SessionStateMachine()
        with pytest.raises(ValueError):
            sm.transition(SessionStatus.EXPIRED, "complete")

    def test_invalid_action_raises(self) -> None:
        sm = SessionStateMachine()
        with pytest.raises(ValueError):
            sm.transition(SessionStatus.OPEN, "invalid_action")
