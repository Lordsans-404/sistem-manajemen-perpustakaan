from django.urls import path

# Views will be imported and registered here as they are implemented.
# Convention: /api/v1/transactions/...
#
# Planned endpoints:
#   GET    /api/v1/transactions/borrows/                  — list all borrow transactions
#   POST   /api/v1/transactions/borrows/                  — create borrow transaction
#   GET    /api/v1/transactions/borrows/{id}/              — retrieve single transaction
#   POST   /api/v1/transactions/borrows/{id}/return/       — mark as returned
#
#   GET    /api/v1/transactions/fines/                    — list all fines
#   POST   /api/v1/transactions/fines/                    — create fine
#   GET    /api/v1/transactions/fines/{id}/               — retrieve fine
#   PATCH  /api/v1/transactions/fines/{id}/pay/           — settle or waive fine

app_name = "transactions"

urlpatterns = [
    # Endpoints will be registered here as views are implemented.
]
