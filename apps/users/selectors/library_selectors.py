from apps.users.models import Library


def get_library_by_id(library_id):
    """Return a single Library by primary key, or None if not found."""
    return Library.objects.filter(pk=library_id).first()


def get_library_by_code(code: str):
    """Return a single Library by code (case-insensitive), or None if not found."""
    return Library.objects.filter(code__iexact=code).first()


def get_all_libraries():
    """Return all libraries ordered by name."""
    return Library.objects.order_by("name")


def get_libraries_by_type(library_type: str):
    """Return all libraries of a given type (e.g. 'central', 'faculty')."""
    return Library.objects.filter(type=library_type).order_by("name")
