from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class ProductFilter(BaseModel):
    keyword: str | None = Field(
        default=None, description="상품명/ID 부분 검색 키워드"
    )
    limit: int = Field(default=20, ge=1, le=100)


class CouponProductRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    goods_id: str
    name: str
    face_value: Decimal
    purchase_price: Decimal
    vendor_status: str
