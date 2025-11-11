from fastapi import APIRouter

from . import auth, campaigns, coupons, cs, health, products, send_query, uploads

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(campaigns.router)
api_router.include_router(send_query.router)
api_router.include_router(uploads.router)
api_router.include_router(coupons.router)
api_router.include_router(cs.router)
