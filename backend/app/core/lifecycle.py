"""
Application status lifecycle.

    draft ──> in_progress <──> ready_for_review ──> submitted

- An application becomes READY_FOR_REVIEW when every required field is
  answered, and drops back to IN_PROGRESS if an answer is later cleared.
- SUBMITTED is final: no further edits and no way back.
Only these transitions are legal; anything else raises a ConflictError.
"""

from app.core.exceptions import ConflictError
from app.models import ApplicationStatus as S

ALLOWED_TRANSITIONS: dict[S, set[S]] = {
    S.DRAFT: {S.IN_PROGRESS},
    S.IN_PROGRESS: {S.READY_FOR_REVIEW},
    S.READY_FOR_REVIEW: {S.IN_PROGRESS, S.SUBMITTED},
    S.SUBMITTED: set(),
}


def can_transition(current: S, target: S) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def assert_transition(current: S, target: S) -> None:
    if not can_transition(current, target):
        raise ConflictError(
            f"An application cannot move from '{current.value}' to '{target.value}'."
        )


def is_editable(status: S) -> bool:
    """Answers can be changed until the application is submitted."""
    return status != S.SUBMITTED