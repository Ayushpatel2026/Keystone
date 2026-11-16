"""Team-on-project lifecycle
 The service layer asks this module "is this move legal,
and what does it do to the project's slots?" and then does the database work.
"""

import enum
import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

# applications -> projects is the allowed dependency direction. We only need the enum,
# to describe project snapshots for the invariant checker.
from app.modules.projects.models import ProjectStatus


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
    (S.SUPERVISOR_ACCEPTS, E.SYSTEM_CLOSE, S.DECLINED_OR_WITHDRAWN, {A.SYSTEM}),
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
        {A.INSTRUCTOR},
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


# ---------------------------------------------------------------------------
# Invariant checker: the PoC success criteria as a function.
# It works on plain snapshots so it stays pure; the service loads them from the database.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectSnapshot:
    id: uuid.UUID
    capacity: int
    slots_reserved: int
    status: ProjectStatus


@dataclass(frozen=True)
class ApplicationSnapshot:
    team_id: uuid.UUID
    project_id: uuid.UUID
    status: ApplicationStatus


class ViolationType(enum.IntEnum):
    SLOT_COUNT_MISMATCH = enum.auto()  # projects.slots_reserved != number of slot-holding apps
    OUTSIDE_CAPACITY_RANGE = enum.auto()  # slots_reserved < 0 or > capacity
    STATUS_CAPACITY_MISMATCH = enum.auto()  # status disagrees with reserved vs capacity
    FULL_WITH_PENDING_APPS = enum.auto()  # a full project still has applications waiting
    MULTIPLE_AGREEMENTS = enum.auto()  # a team is committed to more than one project
    AGREED_BUT_HOLDS_SLOT = enum.auto()  # an agreed team still holds a slot on another project
    AGREED_WITH_PENDING_APPS = enum.auto()  # an agreed team still has applications waiting


# frozen=True makes instances immutable and comparable, which keeps test assertions simple.
@dataclass(frozen=True)
class Violation:
    type: ViolationType
    # The project id for project-level rules, the team id for team-level rules.
    entity_id: uuid.UUID
    message: str


# only called in tests right now, but maybe a modified version of this could be used after
# every action to assert the invariant holds.
def find_violations(
    projects: Iterable[ProjectSnapshot],
    applications: Iterable[ApplicationSnapshot],
) -> list[Violation]:
    # Returns every broken rule; an empty list means the state is consistent.
    # Run it after every action in the PoC demo and tests.
    violations: list[Violation] = []

    # Group applications once so each project/team check below is a dictionary lookup.
    # defaultdict(list) returns an empty list for ids with no applications.
    by_project: dict[uuid.UUID, list[ApplicationSnapshot]] = defaultdict(list)
    by_team: dict[uuid.UUID, list[ApplicationSnapshot]] = defaultdict(list)
    for app in applications:
        by_project[app.project_id].append(app)
        by_team[app.team_id].append(app)

    for project in projects:
        apps = by_project[project.id]
        holding = sum(1 for a in apps if holds_slot(a.status))

        # the stored counter equals the number of slot-holding applications.
        if project.slots_reserved != holding:
            violations.append(
                Violation(
                    ViolationType.SLOT_COUNT_MISMATCH,
                    project.id,
                    f"slots_reserved={project.slots_reserved} but {holding} apps hold a slot",
                )
            )

        # never over capacity (or negative).
        if not 0 <= project.slots_reserved <= project.capacity:
            violations.append(
                Violation(
                    ViolationType.OUTSIDE_CAPACITY_RANGE,
                    project.id,
                    f"slots_reserved={project.slots_reserved} outside 0..{project.capacity}",
                )
            )

        # open exactly when reserved < capacity, full otherwise.
        # CLOSED is set by the selection deadline, not by capacity, so it is exempt.
        if project.status != ProjectStatus.CLOSED:
            expected = (
                ProjectStatus.FULL
                if project.slots_reserved >= project.capacity
                else ProjectStatus.OPEN
            )
            if project.status != expected:
                violations.append(
                    Violation(
                        ViolationType.STATUS_CAPACITY_MISMATCH,
                        project.id,
                        f"status is {project.status.value}, expected {expected.value}",
                    )
                )

        # a full project has no pending applications.
        if project.status == ProjectStatus.FULL and any(is_pending(a.status) for a in apps):
            violations.append(
                Violation(
                    ViolationType.FULL_WITH_PENDING_APPS,
                    project.id,
                    "project is full but has pending applications",
                )
            )

    for team_id, apps in by_team.items():
        agreed = [a for a in apps if has_agreement(a.status)]
        # at most one agreed project per team.
        if len(agreed) > 1:
            violations.append(
                Violation(
                    ViolationType.MULTIPLE_AGREEMENTS,
                    team_id,
                    f"team has {len(agreed)} agreements",
                )
            )

        if agreed:
            # An agreed team holds no slot anywhere else. A slot-holding application that is
            # not itself an agreement can only be a lingering SUPERVISOR_ACCEPTS.
            lingering = [a for a in apps if holds_slot(a.status) and not has_agreement(a.status)]
            if lingering:
                violations.append(
                    Violation(
                        ViolationType.AGREED_BUT_HOLDS_SLOT,
                        team_id,
                        "team has an agreement but still holds a slot on another project",
                    )
                )

            # an agreed team has no pending applications.
            if any(is_pending(a.status) for a in apps):
                violations.append(
                    Violation(
                        ViolationType.AGREED_WITH_PENDING_APPS,
                        team_id,
                        "team has an agreement but still has pending applications",
                    )
                )

    return violations
