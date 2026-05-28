from apps.catalog.models import Book


def get_book_by_id(book_id):
    """Return a Book by primary key, or None if not found."""
    return Book.objects.filter(pk=book_id).first()


def get_all_books():
    """Return all books ordered by title."""
    return Book.objects.order_by("title")


def search_books(query: str):
    """
    Search books by title, author, or category.
    Uses icontains for case-insensitive partial matching.
    """
    return (
        Book.objects
        .filter(
            # title OR author OR category match
            title__icontains=query,
        )
        | Book.objects.filter(author__icontains=query)
        | Book.objects.filter(category__icontains=query)
    ).distinct().order_by("title")


def get_books_by_category(category: str):
    """Return all books belonging to a specific category."""
    return Book.objects.filter(category__iexact=category).order_by("title")


def get_books_by_author(author: str):
    """Return all books by a specific author (case-insensitive)."""
    return Book.objects.filter(author__icontains=author).order_by("title")
