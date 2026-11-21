import pytest

from app.modules.projects.lifecycle import (
    CapacityInvariantError,
    accepts_applications,
    derive_status,
)
from app.modules.projects.models import ProjectStatus

OPEN, FULL, CLOSED = ProjectStatus.OPEN, ProjectStatus.FULL, ProjectStatus.CLOSED


@pytest.mark.parametrize(
    ("current", "capacity", "reserved", "expected"),
    [
        (OPEN, 2, 0, OPEN),  # nothing reserved
        (OPEN, 2, 1, OPEN),  # partly reserved stays open
        (OPEN, 2, 2, FULL),  # last slot taken
        (OPEN, 1, 1, FULL),  # capacity-1 project fills on first acceptance
        (FULL, 2, 1, OPEN),  # a released slot reopens a full project
        (FULL, 2, 2, FULL),  # unchanged
        (CLOSED, 2, 0, CLOSED),  # closed never reopens
        (CLOSED, 2, 2, CLOSED),
    ],
)
def test_derive_status(current, capacity, reserved, expected):
    assert derive_status(current, capacity, reserved) == expected


@pytest.mark.parametrize("reserved", [-1, 3])
def test_out_of_range_reservation_raises(reserved):
    # Over capacity or negative means a bug upstream and must fail loudly.
    with pytest.raises(CapacityInvariantError):
        derive_status(OPEN, 2, reserved)


def test_only_open_accepts_applications():
    assert accepts_applications(OPEN)
    assert not accepts_applications(FULL)
    assert not accepts_applications(CLOSED)
