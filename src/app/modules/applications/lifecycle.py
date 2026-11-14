"""Team-on-project lifecycle
 The service layer asks this module "is this move legal,
and what does it do to the project's slots?" and then does the database work.
"""

import enum
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

# applications -> projects is the allowed dependency direction. We only need the enum,
# to describe project snapshots for the invariant checker.


class ApplicationStatus(enum.StrEnum):
    # Values are what gets stored in the database.
    # The longest is 30 characters, which is why the model's column length is 40.
    APPLIED = "applied"  # no slot used
    SUPERVISOR_ACCEPTS = "supervisor_accepts"  # supervisor said yes, slot reserved
    AGREED = "agreed"  # both sides said yes
    TEAM_PROJECT_SUBMITTED = "team_project_submitted"
    TEAM_PROJECT_UNDER_REVIEW = "team_project_under_review"
    TEAM_PROJECT_CHANGES_REQUESTED = "team_project_changes_requested"
    APPROVED = "approved"
    APPROVED_CHANGE_UNDER_REVIEW = "approved_change_under_review"  # approval stays in effect
    TEAM_PROJECT_REJECTED = "team_project_rejected"  # terminal, slot released
    DECLINED_OR_WITHDRAWN = "declined_or_withdrawn"  # terminal, slot released if held


class ApplicationEvent(enum.StrEnum):
    # Things that can happen to an application. Each is an edge label in the diagram.
    SUPERVISOR_ACCEPT = "supervisor_accept"
    SUPERVISOR_DECLINE = "supervisor_decline"
    TEAM_ACCEPT = "team_accept"
    TEAM_WITHDRAW = "team_withdraw"
    # Automatic closure: the project filled up, or the team agreed to a different project.
    SYSTEM_CLOSE = "system_close"
    SUBMIT = "submit"
    FORWARD_TO_REVIEW = "forward_to_review"
    INSTRUCTOR_APPROVE = "instructor_approve"
    INSTRUCTOR_REQUEST_CHANGES = "instructor_request_changes"
    TEAM_RESUBMIT = "team_resubmit"
    INSTRUCTOR_REJECT = "instructor_reject"
    TEAM_SUBMIT_CHANGE = "team_submit_change"
    INSTRUCTOR_ACCEPT_CHANGE = "instructor_accept_change"
    INSTRUCTOR_REJECT_CHANGE = "instructor_reject_change"
    TEAM_DISSOLVE = "team_dissolve"


class Actor(enum.StrEnum):
    # Who is allowed to trigger an event.
    SUPERVISOR = "supervisor"
    TEAM = "team"
    INSTRUCTOR = "instructor"
    TA = "ta"
    SYSTEM = "system"


# A freshly created application always starts here. Creation is not an edge in the table
# because there is no "from" status, the apply service validates it instead.
INITIAL_STATUS = ApplicationStatus.APPLIED

# Statuses where the team and supervisor have both said yes and the team is committed
# to this project. A team may be in at most one of these at a time.
HAS_AGREEMENT: frozenset[ApplicationStatus] = frozenset(
    {
        ApplicationStatus.AGREED,
        ApplicationStatus.TEAM_PROJECT_SUBMITTED,
        ApplicationStatus.TEAM_PROJECT_UNDER_REVIEW,
        ApplicationStatus.TEAM_PROJECT_CHANGES_REQUESTED,
        ApplicationStatus.APPROVED,
        ApplicationStatus.APPROVED_CHANGE_UNDER_REVIEW,
    }
)

# Statuses that occupy one of the project's slots (the R in the diagram). Slot changes are
# DERIVED from this set: a transition that enters it reserves a slot, one that leaves it
# releases one. Deriving avoids a hand-written slot delta per edge that could disagree.
HOLDS_SLOT: frozenset[ApplicationStatus] = (
    frozenset({ApplicationStatus.SUPERVISOR_ACCEPTS}) | HAS_AGREEMENT
)

# Waiting for a supervisor decision. Must not exist on a full project or for an agreed team.
PENDING: frozenset[ApplicationStatus] = frozenset({ApplicationStatus.APPLIED})

# No way out of these for now. We might allow reopening a rejected application in the future,
# but POC does not need it.
TERMINAL: frozenset[ApplicationStatus] = frozenset(
    {ApplicationStatus.TEAM_PROJECT_REJECTED, ApplicationStatus.DECLINED_OR_WITHDRAWN}
)


def holds_slot(status: ApplicationStatus) -> bool:
    return status in HOLDS_SLOT


def has_agreement(status: ApplicationStatus) -> bool:
    return status in HAS_AGREEMENT


def is_pending(status: ApplicationStatus) -> bool:
    return status in PENDING


class InvalidTransitionError(Exception):
    # The event is not allowed from the current status, e.g. accepting an application that
    # was already withdrawn. The typical cause is a stale view; routers map it to 409.
    pass


class ActorNotPermittedError(Exception):
    # The event exists from this status but this kind of actor may not trigger it.
    pass


@dataclass(frozen=True)
class Transition:
    target: ApplicationStatus
    actors: frozenset[Actor]


@dataclass(frozen=True)
class TransitionOutcome:
    new_status: ApplicationStatus
    # +1 reserves a slot, -1 releases one, 0 leaves the project's slot count alone.
    slot_delta: int


S = ApplicationStatus
E = ApplicationEvent
A = Actor

# (from status, event, to status, actors allowed to trigger it).
# Written as a list of rows so it reads like the diagram, one edge per line.
_EDGES: list[tuple[S, E, S, set[Actor]]] = [
    # --- Selection: the supervisor and team agree ---
    (S.APPLIED, E.SUPERVISOR_ACCEPT, S.SUPERVISOR_ACCEPTS, {A.SUPERVISOR}),
    (S.APPLIED, E.SUPERVISOR_DECLINE, S.DECLINED_OR_WITHDRAWN, {A.SUPERVISOR}),
    (S.APPLIED, E.TEAM_WITHDRAW, S.DECLINED_OR_WITHDRAWN, {A.TEAM}),
    (S.APPLIED, E.SYSTEM_CLOSE, S.DECLINED_OR_WITHDRAWN, {A.SYSTEM}),
    (S.SUPERVISOR_ACCEPTS, E.TEAM_ACCEPT, S.AGREED, {A.TEAM}),
    (S.SUPERVISOR_ACCEPTS, E.SUPERVISOR_DECLINE, S.DECLINED_OR_WITHDRAWN, {A.SUPERVISOR}),
    (S.SUPERVISOR_ACCEPTS, E.TEAM_WITHDRAW, S.DECLINED_OR_WITHDRAWN, {A.TEAM}),
    # --- Approval: submission and review ---
    # In external approval mode the instructor or TA records the submission by hand,
    # which is why INSTRUCTOR and TA are also allowed here.
    (S.AGREED, E.SUBMIT, S.TEAM_PROJECT_SUBMITTED, {A.TEAM, A.INSTRUCTOR, A.TA}),
    (S.AGREED, E.TEAM_WITHDRAW, S.DECLINED_OR_WITHDRAWN, {A.TEAM}),
    (S.TEAM_PROJECT_SUBMITTED, E.FORWARD_TO_REVIEW, S.TEAM_PROJECT_UNDER_REVIEW, {A.SYSTEM}),
    (S.TEAM_PROJECT_SUBMITTED, E.TEAM_WITHDRAW, S.DECLINED_OR_WITHDRAWN, {A.TEAM}),
    (S.TEAM_PROJECT_UNDER_REVIEW, E.INSTRUCTOR_APPROVE, S.APPROVED, {A.INSTRUCTOR, A.TA}),
    (
        S.TEAM_PROJECT_UNDER_REVIEW,
        E.INSTRUCTOR_REQUEST_CHANGES,
        S.TEAM_PROJECT_CHANGES_REQUESTED,
        {A.INSTRUCTOR, A.TA},
    ),
    (
        S.TEAM_PROJECT_UNDER_REVIEW,
        E.INSTRUCTOR_REJECT,
        S.TEAM_PROJECT_REJECTED,
        {A.INSTRUCTOR, A.TA},
    ),
    (S.TEAM_PROJECT_UNDER_REVIEW, E.TEAM_WITHDRAW, S.DECLINED_OR_WITHDRAWN, {A.TEAM}),
    (S.TEAM_PROJECT_CHANGES_REQUESTED, E.TEAM_RESUBMIT, S.TEAM_PROJECT_SUBMITTED, {A.TEAM}),
    (S.TEAM_PROJECT_CHANGES_REQUESTED, E.TEAM_WITHDRAW, S.DECLINED_OR_WITHDRAWN, {A.TEAM}),
    # --- After approval ---
    (S.APPROVED, E.TEAM_SUBMIT_CHANGE, S.APPROVED_CHANGE_UNDER_REVIEW, {A.TEAM}),
    # Dissolving an approved team needs the instructor to confirm, hence INSTRUCTOR.
    (S.APPROVED, E.TEAM_DISSOLVE, S.DECLINED_OR_WITHDRAWN, {A.INSTRUCTOR}),
    # Accepting or rejecting a change both return to APPROVED. The original approval was
    # never revoked; accepting also updates the record, but that is not a status matter.
    (S.APPROVED_CHANGE_UNDER_REVIEW, E.INSTRUCTOR_ACCEPT_CHANGE, S.APPROVED, {A.INSTRUCTOR, A.TA}),
    (S.APPROVED_CHANGE_UNDER_REVIEW, E.INSTRUCTOR_REJECT_CHANGE, S.APPROVED, {A.INSTRUCTOR, A.TA}),
    (
        S.APPROVED_CHANGE_UNDER_REVIEW,
        E.TEAM_DISSOLVE,
        S.DECLINED_OR_WITHDRAWN,
        {A.INSTRUCTOR, A.TA},
    ),
]


def _build_table(
    edges: Iterable[tuple[S, E, S, set[Actor]]],
) -> Mapping[tuple[S, E], Transition]:
    table: dict[tuple[S, E], Transition] = {}
    for source, event, target, actors in edges:
        key = (source, event)

        # A plain dict literal would silently let a duplicate key overwrite an earlier edge.
        if key in table:
            raise ValueError(f"duplicate transition for {key}")

        table[key] = Transition(target=target, actors=frozenset(actors))

    # Read-only view, so nothing can modify the table at runtime by accident.
    return MappingProxyType(table)


TRANSITIONS: Mapping[tuple[S, E], Transition] = _build_table(_EDGES)


def apply_event(
    current: ApplicationStatus, event: ApplicationEvent, actor: Actor
) -> TransitionOutcome:

    # The single entry point for every status change. The service calls this, then applies
    # outcome.new_status to the row and outcome.slot_delta to the project.
    transition = TRANSITIONS.get((current, event))

    if transition is None:
        raise InvalidTransitionError(f"{event.value} is not allowed from {current.value}")

    if actor not in transition.actors:
        raise ActorNotPermittedError(
            f"{actor.value} may not trigger {event.value} from {current.value}"
        )

    # Derived slot delta: bool -> int is 1/0, so the difference is +1, 0 or -1.
    delta = int(holds_slot(transition.target)) - int(holds_slot(current))
    return TransitionOutcome(new_status=transition.target, slot_delta=delta)
