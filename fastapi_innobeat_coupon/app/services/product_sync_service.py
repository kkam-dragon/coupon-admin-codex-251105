from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import CouponProduct, ProductSyncLog
from app.services import coufun_service
from app.services.coufun_service import CoufunAPIError


def sync_coufun_products(db: Session) -> dict:
    request_payload = {"endpoint": "coufunProduct.do"}
    try:
        response = coufun_service.fetch_goods_list()
        products = response.products
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
            request_payload={**request_payload, "count": len(products)},
            response_code=response.result_code or "00",
            synced_count=synced,
            status="SUCCESS",
        )
        db.add(log)
        db.commit()
        return {"synced": synced, "result_code": response.result_code}
    except CoufunAPIError as exc:
        db.rollback()
        failure_log = ProductSyncLog(
            sync_type="COUFUN_GOODS",
            request_payload=request_payload,
            response_code=exc.code or "ERROR",
            synced_count=0,
            status="FAILED",
            error_detail=str(exc),
        )
        db.add(failure_log)
        db.commit()
        raise
