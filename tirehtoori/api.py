from django.conf import settings
from ninja import NinjaAPI

api = NinjaAPI()

if settings.ENABLE_REDIRECT_APP:
    from redirect.api import router as redirect_router

    api.add_router("/", redirect_router)
