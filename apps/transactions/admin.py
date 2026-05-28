from django.contrib import admin

from apps.transactions.models import BorrowTransaction, Fine


@admin.register(BorrowTransaction)
class BorrowTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "member", "book_copy", "library",
        "borrow_date", "due_date", "return_date", "is_overdue",
    )
    search_fields = ("member__user__email", "member__user__name", "book_copy__book__title")
    list_filter = ("library", "borrow_date")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-borrow_date",)

    @admin.display(boolean=True, description="Overdue")
    def is_overdue(self, obj):
        return obj.is_overdue


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = ("borrow_transaction", "amount", "payment_status", "paid_date")
    search_fields = ("borrow_transaction__member__user__email",)
    list_filter = ("payment_status",)
    readonly_fields = ("id", "created_at", "updated_at")
