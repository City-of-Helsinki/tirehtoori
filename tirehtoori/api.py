from ninja import NinjaAPI
from redirect.api import router as redirect_router

api = NinjaAPI()

api.add_router("/", redirect_router)
