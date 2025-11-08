from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import CouponProduct, ProductSyncLog
from app.services import coufun_service


def sync_coufun_products(db: Session) -> dict:
    products = coufun_service.fetch_goods_list()
    synced = 0

    for product in products:
        existing = db.scalar(
            select(CouponProduct).where(CouponProduct.goods_id == product.goods_id)
        )
        if not existing:
            existing = CouponProduct(goods_id=product.goods_id)
            db.add(existing)
        existing.name = product.name
        existing.face_value = product.face_value
        existing.purchase_price = product.purchase_price
        existing.valid_days = product.valid_days
        existing.vendor_status = product.status
        synced += 1

    log = ProductSyncLog(
        sync_type="COUFUN_GOODS",
        request_payload={"count": len(products)},
        response_code="SUCCESS",
        synced_count=synced,
        status="SUCCESS",
    )
    db.add(log)
    db.commit()

    return {"synced": synced}
