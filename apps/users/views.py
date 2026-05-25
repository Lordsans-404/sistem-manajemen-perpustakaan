from rest_framework.views import APIView

# Views must remain thin.
# Delegate all business logic to services, all queries to selectors.
#
# Pattern:
#   1. Deserialize input via InputSerializer
#   2. Call service / selector
#   3. Serialize output via OutputSerializer
#   4. Return standard response (see convention §8)
