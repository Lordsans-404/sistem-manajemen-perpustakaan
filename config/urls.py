from django.contrib import admin
from django.urls import include, path

# ---------------------------------------------------------------------------
# Root URL configuration
# API version prefix: /api/v1/
# ---------------------------------------------------------------------------
#
# URL namespace map:
#   /api/v1/users/         → apps.users.urls        (app_name="users")
#   /api/v1/catalog/       → apps.catalog.urls       (app_name="catalog")
#   /api/v1/transactions/  → apps.transactions.urls  (app_name="transactions")

api_v1_patterns = [
    path("users/", include("apps.users.urls", namespace="users")),
    path("catalog/", include("apps.catalog.urls", namespace="catalog")),
    path("transactions/", include("apps.transactions.urls", namespace="transactions")),
]

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),

    # API v1
    path("api/v1/", include((api_v1_patterns, "api_v1"))),

    # DRF browsable API auth endpoints (development only — guard with DEBUG in production)
    path("api-auth/", include("rest_framework.urls")),
]
