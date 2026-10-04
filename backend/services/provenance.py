"""Portable metadata is historical attribution, never proof of artifact inspection."""

from domain.models import Project, ProjectObject, Provenance, Verification


def imported_object(obj: ProjectObject, anchors: set[tuple[str, int, str]]) -> ProjectObject:
    # rdw-app-1 carries source identity/anchors but no inspectable analysis artifacts.
    # Remove unavailable inspections rather than granting authority from an imported flag.
    checks = tuple(check for check in obj.checks if check.provenance == Provenance.USER_REPORTED)
    dispositions = tuple(
        disposition.model_copy(
            update={
                "disposition": Verification.UNRESOLVED,
                "reason": "Portable import contains no source passages to recheck support; unresolved. "
                + disposition.reason,
                "source_refs": tuple(
                    ref
                    for ref in disposition.source_refs
                    if (ref.document_id, ref.version, ref.anchor_id) in anchors
                ),
            }
        )
        if disposition.disposition == Verification.SUPPORTED
        else disposition
        for disposition in obj.support_dispositions
    )
    return obj.model_copy(
        update={
            "imported": True,
            "checks": checks,
            "support_dispositions": dispositions,
            "imported_support_history": obj.imported_support_history or obj.support_dispositions,
        }
    )


def assert_context_provenance(project: Project) -> None:
    for obj in project.objects:
        if obj.imported and any(
            check.provenance != Provenance.USER_REPORTED for check in obj.checks
        ):
            raise ValueError("IMPORTED_INSPECTION_AUTHORITY_UNAVAILABLE")
        if any(
            disposition.disposition == Verification.SUPPORTED and not disposition.source_refs
            for disposition in obj.support_dispositions
        ):
            raise ValueError("SUPPORT_PROVENANCE_UNAVAILABLE")
