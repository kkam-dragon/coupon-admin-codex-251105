from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.domain import CouponProduct
from app.schemas.products import ProductFilter


def build_product_query(filters: ProductFilter) -> Select[tuple[CouponProduct]]:
    query = select(CouponProduct).order_by(CouponProduct.name.asc())
    if filters.keyword:
        keyword = f"%{filters.keyword}%"
        query = query.where(
            (CouponProduct.name.ilike(keyword))
            | (CouponProduct.goods_id.ilike(keyword))
        )
    return query.limit(filters.limit)


def list_products(db: Session, filters: ProductFilter) -> list[CouponProduct]:
    result = db.execute(build_product_query(filters))
    return list(result.scalars().all())
