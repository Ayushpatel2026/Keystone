import uuid

import pytest

from app.modules.applications.lifecycle import (
    HAS_AGREEMENT,
    HOLDS_SLOT,
    TERMINAL,
    TRANSITIONS,
    A,
    ActorNotPermittedError,
    ApplicationSnapshot,
    E,
    InvalidTransitionError,
    ProjectSnapshot,
    ViolationType,
    apply_event,
    find_violations,
)
from app.modules.applications.lifecycle import (
    ApplicationStatus as S,
)
from app.modules.projects.models import ProjectStatus as P

# ---------------------------------------------------------------------------
# Transition table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("current", "event", "actor", "expected_status", "expected_delta"),
    [
        # Reserving a slot happens only when the supervisor accepts.
        (S.APPLIED, E.SUPERVISOR_ACCEPT, A.SUPERVISOR, S.SUPERVISOR_ACCEPTS, +1),
        # Declining or withdrawing before any acceptance never touches the slot count.
        (S.APPLIED, E.SUPERVISOR_DECLINE, A.SUPERVISOR, S.DECLINED_OR_WITHDRAWN, 0),
        (S.APPLIED, E.TEAM_WITHDRAW, A.TEAM, S.DECLINED_OR_WITHDRAWN, 0),
        (S.APPLIED, E.SYSTEM_CLOSE, A.SYSTEM, S.DECLINED_OR_WITHDRAWN, 0),
        # Team agreeing keeps the slot already reserved: no second increment.
        (S.SUPERVISOR_ACCEPTS, E.TEAM_ACCEPT, A.TEAM, S.AGREED, 0),
        # Every exit from a slot-holding status releases exactly one slot.
        (S.SUPERVISOR_ACCEPTS, E.SUPERVISOR_DECLINE, A.SUPERVISOR, S.DECLINED_OR_WITHDRAWN, -1),
        (S.SUPERVISOR_ACCEPTS, E.TEAM_WITHDRAW, A.TEAM, S.DECLINED_OR_WITHDRAWN, -1),
        (S.SUPERVISOR_ACCEPTS, E.SYSTEM_CLOSE, A.SYSTEM, S.DECLINED_OR_WITHDRAWN, -1),
        (S.AGREED, E.TEAM_WITHDRAW, A.TEAM, S.DECLINED_OR_WITHDRAWN, -1),
        (
            S.TEAM_PROJECT_UNDER_REVIEW,
            E.INSTRUCTOR_REJECT,
            A.INSTRUCTOR,
            S.TEAM_PROJECT_REJECTED,
            -1,
        ),
        (S.APPROVED, E.TEAM_DISSOLVE, A.INSTRUCTOR, S.DECLINED_OR_WITHDRAWN, -1),
        # Moves between slot-holding statuses keep the slot.
        (S.AGREED, E.SUBMIT, A.TEAM, S.TEAM_PROJECT_SUBMITTED, 0),
        (S.AGREED, E.SUBMIT, A.INSTRUCTOR, S.TEAM_PROJECT_SUBMITTED, 0),  # external approval mode
        (S.TEAM_PROJECT_SUBMITTED, E.FORWARD_TO_REVIEW, A.SYSTEM, S.TEAM_PROJECT_UNDER_REVIEW, 0),
        (S.TEAM_PROJECT_UNDER_REVIEW, E.INSTRUCTOR_APPROVE, A.INSTRUCTOR, S.APPROVED, 0),
        (
            S.TEAM_PROJECT_UNDER_REVIEW,
            E.INSTRUCTOR_REQUEST_CHANGES,
            A.INSTRUCTOR,
            S.TEAM_PROJECT_CHANGES_REQUESTED,
            0,
        ),
        (S.TEAM_PROJECT_CHANGES_REQUESTED, E.TEAM_RESUBMIT, A.TEAM, S.TEAM_PROJECT_SUBMITTED, 0),
        # Changes after approval never revoke the approval.
        (S.APPROVED, E.TEAM_SUBMIT_CHANGE, A.TEAM, S.APPROVED_CHANGE_UNDER_REVIEW, 0),
        (S.APPROVED_CHANGE_UNDER_REVIEW, E.INSTRUCTOR_ACCEPT_CHANGE, A.INSTRUCTOR, S.APPROVED, 0),
        (S.APPROVED_CHANGE_UNDER_REVIEW, E.INSTRUCTOR_REJECT_CHANGE, A.INSTRUCTOR, S.APPROVED, 0),
    ],
)
def test_transition_outcome(current, event, actor, expected_status, expected_delta):
    outcome = apply_event(current, event, actor)
    assert outcome.new_status == expected_status
    assert outcome.slot_delta == expected_delta


@pytest.mark.parametrize(
    ("current", "event"),
    [
        (S.APPLIED, E.TEAM_ACCEPT),  # team can't accept before the supervisor does
        (S.APPLIED, E.SUBMIT),  # can't submit without an agreement
        (S.SUPERVISOR_ACCEPTS, E.SUPERVISOR_ACCEPT),  # accepting twice
        (S.AGREED, E.INSTRUCTOR_APPROVE),  # must go through submission and review
        (S.TEAM_PROJECT_SUBMITTED, E.INSTRUCTOR_APPROVE),  # must be forwarded to review first
    ],
)
def test_illegal_events_are_rejected(current, event):
    with pytest.raises(InvalidTransitionError):
        apply_event(current, event, A.SYSTEM)


def test_wrong_actor_is_rejected():
    # The edge exists, but a team can't accept on the supervisor's behalf.
    with pytest.raises(ActorNotPermittedError):
        apply_event(S.APPLIED, E.SUPERVISOR_ACCEPT, A.TEAM)


@pytest.mark.parametrize("terminal", sorted(TERMINAL))
def test_terminal_statuses_have_no_outgoing_edges(terminal):
    assert not [key for key in TRANSITIONS if key[0] == terminal]


def test_slot_is_reserved_only_by_supervisor_accept_from_applied():
    # Guards the key invariant: there is exactly one way to take a slot.
    for (source, event), transition in TRANSITIONS.items():
        if source not in HOLDS_SLOT and transition.target in HOLDS_SLOT:
            assert (source, event) == (S.APPLIED, E.SUPERVISOR_ACCEPT)


def test_agreement_statuses_are_a_subset_of_slot_holding_statuses():
    # An agreed team always holds its slot.
    assert HAS_AGREEMENT <= HOLDS_SLOT


def test_every_status_except_applied_is_reachable():
    targets = {t.target for t in TRANSITIONS.values()}
    assert set(S) - targets == {S.APPLIED}


# ---------------------------------------------------------------------------
# Invariant checker
# ---------------------------------------------------------------------------

TEAM_1, TEAM_2 = uuid.uuid4(), uuid.uuid4()
PROJ_A, PROJ_B = uuid.uuid4(), uuid.uuid4()


def proj(pid, capacity=2, reserved=0, status=P.OPEN):
    return ProjectSnapshot(pid, capacity, reserved, status)


def app(team, project, status):
    return ApplicationSnapshot(team, project, status)


def test_consistent_state_has_no_violations():
    projects = [
        proj(PROJ_A, capacity=1, reserved=1, status=P.FULL),
        proj(PROJ_B, capacity=2, reserved=0),
    ]
    apps = [app(TEAM_1, PROJ_A, S.AGREED), app(TEAM_2, PROJ_B, S.APPLIED)]
    assert find_violations(projects, apps) == []


def test_apply_changes_no_project_state():
    # The state the apply endpoint produces: pending applications, zero slots reserved.
    projects = [proj(PROJ_A), proj(PROJ_B)]
    apps = [app(TEAM_1, PROJ_A, S.APPLIED), app(TEAM_1, PROJ_B, S.APPLIED)]
    assert find_violations(projects, apps) == []


def test_counter_must_match_slot_holding_applications():
    projects = [proj(PROJ_A, reserved=1)]  # counter says 1 but nothing holds a slot
    violations = find_violations(projects, [app(TEAM_1, PROJ_A, S.APPLIED)])
    assert len(violations) == 1
    assert violations[0].type == ViolationType.SLOT_COUNT_MISMATCH
    assert violations[0].entity_id == PROJ_A


def test_reserved_over_capacity_is_flagged():
    projects = [proj(PROJ_A, capacity=1, reserved=2, status=P.FULL)]
    apps = [app(TEAM_1, PROJ_A, S.SUPERVISOR_ACCEPTS), app(TEAM_2, PROJ_A, S.SUPERVISOR_ACCEPTS)]
    violations = find_violations(projects, apps)
    assert len(violations) == 1
    assert violations[0].type == ViolationType.OUTSIDE_CAPACITY_RANGE
    assert violations[0].entity_id == PROJ_A


def test_status_must_match_capacity():
    # All slots reserved but the project still says open.
    projects = [proj(PROJ_A, capacity=1, reserved=1, status=P.OPEN)]
    violations = find_violations(projects, [app(TEAM_1, PROJ_A, S.SUPERVISOR_ACCEPTS)])
    assert len(violations) == 1
    assert violations[0].type == ViolationType.STATUS_CAPACITY_MISMATCH
    assert violations[0].entity_id == PROJ_A


def test_closed_project_is_exempt_from_the_status_rule():
    projects = [proj(PROJ_A, capacity=2, reserved=0, status=P.CLOSED)]
    assert find_violations(projects, []) == []


def test_full_project_must_have_no_pending_applications():
    projects = [proj(PROJ_A, capacity=1, reserved=1, status=P.FULL)]
    apps = [app(TEAM_1, PROJ_A, S.SUPERVISOR_ACCEPTS), app(TEAM_2, PROJ_A, S.APPLIED)]
    violations = find_violations(projects, apps)
    assert len(violations) == 1
    assert violations[0].type == ViolationType.FULL_WITH_PENDING_APPS
    assert violations[0].entity_id == PROJ_A


def test_team_with_agreement_cannot_hold_a_slot_elsewhere():
    projects = [proj(PROJ_A, reserved=1), proj(PROJ_B, reserved=1)]
    apps = [app(TEAM_1, PROJ_A, S.AGREED), app(TEAM_1, PROJ_B, S.SUPERVISOR_ACCEPTS)]
    violations = find_violations(projects, apps)
    assert len(violations) == 1
    assert violations[0].type == ViolationType.AGREED_BUT_HOLDS_SLOT
    assert violations[0].entity_id == TEAM_1


def test_team_with_agreement_cannot_have_pending_applications():
    projects = [proj(PROJ_A, reserved=1), proj(PROJ_B)]
    apps = [app(TEAM_1, PROJ_A, S.AGREED), app(TEAM_1, PROJ_B, S.APPLIED)]
    violations = find_violations(projects, apps)
    assert len(violations) == 1
    assert violations[0].type == ViolationType.AGREED_WITH_PENDING_APPS
    assert violations[0].entity_id == TEAM_1


def test_team_cannot_have_two_agreements():
    projects = [proj(PROJ_A, reserved=1), proj(PROJ_B, reserved=1)]
    apps = [app(TEAM_1, PROJ_A, S.AGREED), app(TEAM_1, PROJ_B, S.APPROVED)]
    violations = find_violations(projects, apps)
    assert len(violations) == 1
    assert violations[0].type == ViolationType.MULTIPLE_AGREEMENTS
    assert violations[0].entity_id == TEAM_1
