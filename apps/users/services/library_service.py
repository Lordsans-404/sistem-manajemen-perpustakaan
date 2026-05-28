import logging

from django.db import transaction

from apps.users.models import Library

logger = logging.getLogger(__name__)


def create_library(*, name: str, type: str, code: str) -> Library:
    """
    Create a new Library branch.
    Code is normalized to UPPER_CASE and checked for uniqueness.
    """
    code = code.strip().upper()
    if Library.objects.filter(code=code).exists():
        raise ValueError(f"Library with code '{code}' already exists.")

    with transaction.atomic():
        library = Library.objects.create(
            name=name.strip(),
            type=type,
            code=code,
        )

    logger.info("library.created library_id=%s code=%s", library.pk, library.code)
    return library


def update_library(
    *,
    library: Library,
    name: str | None = None,
    type: str | None = None,
    code: str | None = None,
) -> Library:
    """
    Partially update a Library.
    If code is changed, uniqueness is re-validated.
    """
    updated_fields = []

    if name is not None:
        library.name = name.strip()
        updated_fields.append("name")

    if type is not None:
        library.type = type
        updated_fields.append("type")

    if code is not None:
        new_code = code.strip().upper()
        if new_code != library.code and Library.objects.filter(code=new_code).exists():
            raise ValueError(f"Library with code '{new_code}' already exists.")
        library.code = new_code
        updated_fields.append("code")

    if updated_fields:
        library.save(update_fields=updated_fields + ["updated_at"])
        logger.info("library.updated library_id=%s fields=%s", library.pk, updated_fields)

    return library


def delete_library(*, library: Library) -> None:
    """
    Delete a Library.
    Will raise ProtectedError if there are staff or book copies referencing it.
    """
    library_id = library.pk
    library.delete()
    logger.info("library.deleted library_id=%s", library_id)
