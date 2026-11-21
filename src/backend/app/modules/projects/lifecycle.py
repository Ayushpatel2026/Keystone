"""Pure project-status rules.
The applications service counts reserved
slots, passes the number in here, and gets back the status the project should have.
"""

from app.modules.projects.models import ProjectStatus


class CapacityInvariantError(Exception):
    # Raised when reserved slots are negative or exceed capacity. A user can't cause this
    # through the API if the application service is correct, so it signals a bug.
    # Failing loudly beats silently writing a corrupt status.
    pass


def accepts_applications(status: ProjectStatus) -> bool:
    # Only an OPEN project takes new applications. FULL means every slot is reserved
    # and CLOSED means the selection period is over.
    return status == ProjectStatus.OPEN


def derive_status(
    current: ProjectStatus,
    capacity: int,
    reserved: int,
) -> ProjectStatus:
    # Status of a listed project is a function of (capacity, reserved slots):
    #   reserved < capacity  -> OPEN
    #   reserved == capacity -> FULL
    # CLOSED is set by the end of the selection period, not by capacity, so it
    # sticks regardless of how many slots are reserved.

    # Guard the invariants first so a bad count can never produce a plausible-looking status.
    if reserved < 0 or reserved > capacity:
        raise CapacityInvariantError(f"reserved={reserved} is outside 0..{capacity}")

    if current == ProjectStatus.CLOSED:
        # A closed project must not reopen just because a slot was released.
        return ProjectStatus.CLOSED

    # The DB check constraint guarantees capacity > 0, so equality here means the project
    # has at least one reserved slot and no free ones.
    return ProjectStatus.FULL if reserved == capacity else ProjectStatus.OPEN
