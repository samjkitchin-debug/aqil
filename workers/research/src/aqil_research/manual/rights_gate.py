"""Rights checks for the action actually taken."""

from __future__ import annotations

from aqil_research.sources.rights import RightsOperation, SourceRightsRecord, source_usable


class RegistrationBlocked(Exception):
    """The write did not happen."""


def require_rights(
    rights: SourceRightsRecord,
    operations: tuple[RightsOperation, ...],
) -> None:
    blocked = [operation.value for operation in operations if not source_usable(rights, operation)]
    if blocked:
        names = ", ".join(blocked)
        raise RegistrationBlocked(
            f"{rights.source_id} is not permitted for {names}",
        )
