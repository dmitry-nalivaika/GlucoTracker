"""Session domain — state machine and business rules.

Pure Python; no SQLAlchemy or Telegram dependencies.
"""

from __future__ import annotations

from glucotrack.models.session import SessionStatus


class InsufficientEntriesError(Exception):
    """Raised when attempting to complete a session without required entries."""

    def __init__(self, food_count: int, cgm_count: int) -> None:
        self.food_count = food_count
        self.cgm_count = cgm_count
        super().__init__(
            f"Session requires ≥1 food photo and ≥1 CGM screenshot "
            f"(got food={food_count}, cgm={cgm_count})."
        )


# Valid transitions: (current_status, action) -> new_status
_TRANSITIONS: dict[tuple[SessionStatus, str], SessionStatus] = {
    (SessionStatus.OPEN, "complete"): SessionStatus.COMPLETED,
    (SessionStatus.OPEN, "expire"): SessionStatus.EXPIRED,
    (SessionStatus.COMPLETED, "analyse"): SessionStatus.ANALYSED,
}


class SessionStateMachine:
    """Validates and applies session status transitions."""

    def can_complete(self, food_count: int, cgm_count: int) -> bool:
        """Return True if the session has the minimum required entries."""
        return food_count >= 1 and cgm_count >= 1

    def validate_completion(self, food_count: int, cgm_count: int) -> None:
        """Raise InsufficientEntriesError if session cannot be completed."""
        if not self.can_complete(food_count, cgm_count):
            raise InsufficientEntriesError(food_count, cgm_count)

    def transition(self, current: SessionStatus, action: str) -> SessionStatus:
        """Return the new status after applying action, or raise ValueError.

        Args:
            current: The current session status.
            action: One of 'complete', 'expire', 'analyse'.

        Returns:
            The new SessionStatus.

        Raises:
            ValueError: If the transition is not valid.
        """
        key = (current, action)
        if key not in _TRANSITIONS:
            raise ValueError(
                f"Invalid transition: status={current.value!r} action={action!r}. "
                f"Valid transitions: {[f'{s.value}→{a}' for (s, a) in _TRANSITIONS]}"
            )
        return _TRANSITIONS[key]
