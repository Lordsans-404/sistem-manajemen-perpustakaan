from django.urls import path

from apps.transactions.views import (
    BorrowDetailView,
    BorrowListView,
    BorrowReturnView,
    FineDetailView,
    FineListView,
    FinePayView,
    FineWaiveView,
)

app_name = "transactions"

urlpatterns = [
    # --- BorrowTransaction ---
    path("borrows/", BorrowListView.as_view(), name="borrow-list"),
    path("borrows/<uuid:pk>/", BorrowDetailView.as_view(), name="borrow-detail"),
    path("borrows/<uuid:pk>/return/", BorrowReturnView.as_view(), name="borrow-return"),

    # --- Fine ---
    path("fines/", FineListView.as_view(), name="fine-list"),
    path("fines/<uuid:pk>/", FineDetailView.as_view(), name="fine-detail"),
    path("fines/<uuid:pk>/pay/", FinePayView.as_view(), name="fine-pay"),
    path("fines/<uuid:pk>/waive/", FineWaiveView.as_view(), name="fine-waive"),
]
