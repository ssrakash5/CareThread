"""
Explicit CareThread state machine (spec section 10). The agent may only
*propose* transitions; this module is the sole place that performs them.
"""
from typing import Optional

ALLOWED_TRANSITIONS = {
    "PROPOSED": {"OPEN", "REJECTED"},
    "OPEN": {"IN_PROGRESS"},
    "IN_PROGRESS": {"AWAITING_EVIDENCE", "CLOSURE_PROPOSED"},
    "AWAITING_EVIDENCE": {"OVERDUE", "IN_PROGRESS", "CLOSURE_PROPOSED"},
    "OVERDUE": {"ESCALATED", "IN_PROGRESS", "CLOSURE_PROPOSED"},
    "ESCALATED": {"IN_PROGRESS", "CLOSURE_PROPOSED"},
    "CLOSURE_PROPOSED": {"CLOSED", "OPEN"},
    "CLOSED": {"OPEN"},  # REOPEN_THREAD
    "REJECTED": set(),
}


class InvalidTransitionError(Exception):
    pass


def validate_transition(current: str, target: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(f"Cannot transition thread from {current} to {target}")
