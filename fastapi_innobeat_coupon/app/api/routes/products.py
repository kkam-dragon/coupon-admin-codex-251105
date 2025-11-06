from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.products import CouponProductRead, ProductFilter
from app.services.product_service import list_products

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[CouponProductRead])
def get_products(filters: ProductFilter = Depends(), db: Session = Depends(get_db)):
    """
    sendCoupon 화면에서 사용할 상품 검색 API.
    """
    products = list_products(db, filters)
    return [CouponProductRead.model_validate(p) for p in products]
