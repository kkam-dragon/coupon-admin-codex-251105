from fastapi import APIRouter

from . import campaigns, coupons, health, products, uploads

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(products.router)
api_router.include_router(campaigns.router)
api_router.include_router(uploads.router)
api_router.include_router(coupons.router)
