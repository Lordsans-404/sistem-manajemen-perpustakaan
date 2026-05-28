from django.contrib import admin

from apps.catalog.models import Book, BookCopy


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "created_at")
    search_fields = ("title", "author", "category")
    list_filter = ("category",)
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("title",)


@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ("book", "library", "condition", "isbn", "publication_year")
    search_fields = ("book__title", "isbn")
    list_filter = ("condition", "library")
    readonly_fields = ("id", "created_at", "updated_at")
