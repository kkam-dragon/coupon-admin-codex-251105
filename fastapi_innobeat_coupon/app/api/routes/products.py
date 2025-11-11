from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.core.roles import DEFAULT_READ_ROLES, DEFAULT_WRITE_ROLES
from app.db.session import get_db
from app.schemas.products import CouponProductRead, ProductFilter
from app.services.product_service import list_products
from app.services.product_sync_service import sync_coufun_products
from app.services.audit_service import log_action

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[CouponProductRead])
def get_products(
    filters: ProductFilter = Depends(),
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles(DEFAULT_READ_ROLES)),
):
    """
    sendCoupon 화면에서 사용할 상품 검색 API.
    """
    products = list_products(db, filters)
    return [CouponProductRead.model_validate(p) for p in products]


@router.post("/sync/coufun")
def sync_coufun_goods(
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles(DEFAULT_WRITE_ROLES)),
):
    """
    COUFUN 상품 목록을 동기화한다.
    """
    try:
        summary = sync_coufun_products(db)
        log_action(
            db,
            user_id=current_user.id,
            action="product.sync",
            target_type="product_sync",
            target_id="COUFUN_GOODS",
            commit=True,
        )
        return summary
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
