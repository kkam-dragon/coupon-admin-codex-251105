from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Index,
    LargeBinary,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base, TimestampMixin


class User(TimestampMixin, AuditMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    enc_name: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    enc_email: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    enc_phone: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Role(TimestampMixin, AuditMixin, Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )


class AuthSession(TimestampMixin, Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    jwt_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(255))


class Client(TimestampMixin, AuditMixin, Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    enc_contact_name: Mapped[bytes | None] = mapped_column(LargeBinary)
    enc_contact_phone: Mapped[bytes | None] = mapped_column(LargeBinary)
    enc_contact_email: Mapped[bytes | None] = mapped_column(LargeBinary)
    sales_manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)


class Campaign(TimestampMixin, AuditMixin, Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campaign_key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    event_name: Mapped[str] = mapped_column(String(100), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sender_number: Mapped[str] = mapped_column(String(20), nullable=False)
    message_title: Mapped[str] = mapped_column(String(120), nullable=False)
    message_body: Mapped[str] = mapped_column(Text, nullable=False)
    banner_asset_id: Mapped[int | None] = mapped_column(ForeignKey("media_assets.id"))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)


class CampaignStatusLog(TimestampMixin, Base):
    __tablename__ = "campaign_status_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    logged_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CampaignProduct(TimestampMixin, AuditMixin, Base):
    __tablename__ = "campaign_products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    coupon_product_id: Mapped[int] = mapped_column(ForeignKey("coupon_products.id"))
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    settle_price: Mapped[float | None] = mapped_column(Numeric(12, 2))


class RecipientBatch(TimestampMixin, AuditMixin, Base):
    __tablename__ = "recipient_batches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    upload_type: Mapped[str] = mapped_column(String(20), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_count: Mapped[int] = mapped_column(Integer, default=0)
    invalid_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class CampaignRecipient(TimestampMixin, AuditMixin, Base):
    __tablename__ = "campaign_recipients"
    __table_args__ = (
        Index("ix_recipient_campaign_status", "campaign_id", "status"),
        Index("ix_recipient_phone_hash", "phone_hash"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("recipient_batches.id", ondelete="SET NULL"))
    enc_phone: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    phone_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    enc_name: Mapped[bytes | None] = mapped_column(LargeBinary)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    validation_error: Mapped[str | None] = mapped_column(String(255))


class RecipientHistory(TimestampMixin, AuditMixin, Base):
    __tablename__ = "recipient_histories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("campaign_recipients.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)


class CouponProduct(TimestampMixin, AuditMixin, Base):
    __tablename__ = "coupon_products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    goods_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    face_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    purchase_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    valid_days: Mapped[int | None] = mapped_column(Integer)
    vendor_status: Mapped[str] = mapped_column(String(20), nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProductSyncLog(TimestampMixin, Base):
    __tablename__ = "product_sync_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sync_type: Mapped[str] = mapped_column(String(30), nullable=False)
    request_payload: Mapped[dict | None] = mapped_column(JSON)
    response_code: Mapped[str | None] = mapped_column(String(30))
    synced_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS", nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text)


class CouponIssue(TimestampMixin, AuditMixin, Base):
    __tablename__ = "coupon_issues"
    __table_args__ = (
        Index("ix_issue_campaign_status", "campaign_id", "status"),
        Index("ix_issue_order_id", "order_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    recipient_id: Mapped[int] = mapped_column(ForeignKey("campaign_recipients.id"))
    order_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    barcode_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    valid_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    vendor_payload: Mapped[dict | None] = mapped_column(JSON)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CouponStatusHistory(TimestampMixin, AuditMixin, Base):
    __tablename__ = "coupon_status_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    coupon_issue_id: Mapped[int] = mapped_column(ForeignKey("coupon_issues.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    status_source: Mapped[str] = mapped_column(String(20), nullable=False)
    status_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    memo: Mapped[str | None] = mapped_column(Text)


class CouponExchangeDetail(TimestampMixin, AuditMixin, Base):
    __tablename__ = "coupon_exchange_details"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    coupon_issue_id: Mapped[int] = mapped_column(ForeignKey("coupon_issues.id", ondelete="CASCADE"))
    exchange_store: Mapped[str | None] = mapped_column(String(100))
    exchange_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remain_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))


class CouponTemplate(TimestampMixin, AuditMixin, Base):
    __tablename__ = "coupon_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    template_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    editor_schema: Mapped[str | None] = mapped_column(Text)
    default_variables: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class MediaAsset(TimestampMixin, AuditMixin, Base):
    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(50))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(64))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class RenderedMmsAsset(TimestampMixin, Base):
    __tablename__ = "rendered_mms_assets"
    __table_args__ = (
        UniqueConstraint("campaign_id", "recipient_id", "template_id", name="uq_render_target"),
        Index("ix_render_campaign_recipient", "campaign_id", "recipient_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    recipient_id: Mapped[int] = mapped_column(ForeignKey("campaign_recipients.id"))
    template_id: Mapped[int | None] = mapped_column(ForeignKey("coupon_templates.id"))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("media_assets.id"))
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64))


class MmsJob(TimestampMixin, AuditMixin, Base):
    __tablename__ = "mms_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    recipient_id: Mapped[int] = mapped_column(ForeignKey("campaign_recipients.id"))
    client_key: Mapped[str] = mapped_column(String(40), nullable=False)
    ums_msg_id: Mapped[str | None] = mapped_column(String(50))
    req_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="READY", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)


class DispatchResult(TimestampMixin, Base):
    __tablename__ = "dispatch_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    mms_job_id: Mapped[int] = mapped_column(ForeignKey("mms_jobs.id", ondelete="CASCADE"))
    done_code: Mapped[str | None] = mapped_column(String(10))
    done_desc: Mapped[str | None] = mapped_column(String(255))
    telco: Mapped[str | None] = mapped_column(String(10))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CsAction(TimestampMixin, AuditMixin, Base):
    __tablename__ = "cs_actions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    coupon_issue_id: Mapped[int] = mapped_column(ForeignKey("coupon_issues.id"))
    recipient_id: Mapped[int] = mapped_column(ForeignKey("campaign_recipients.id"))
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    performed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result_status: Mapped[str | None] = mapped_column(String(20))


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[str | None] = mapped_column(String(50))
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ReportExport(TimestampMixin, AuditMixin, Base):
    __tablename__ = "report_exports"
    __table_args__ = (
        Index("ix_report_type_status", "report_type", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False)
    filter_payload: Mapped[dict | None] = mapped_column(JSON)
    row_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    file_path: Mapped[str | None] = mapped_column(String(255))


class QueryCursorBookmark(TimestampMixin, Base):
    __tablename__ = "query_cursor_bookmarks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    query_type: Mapped[str] = mapped_column(String(30), nullable=False)
    last_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    filters_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class SnapMsgView(TimestampMixin, Base):
    """
    SNAP Agent의 UMS_MSG / UMS_LOG를 미러링하는 테이블.
    """

    __tablename__ = "snap_msg_view"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ums_msg_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    client_key: Mapped[str] = mapped_column(String(40), nullable=False)
    req_ch: Mapped[str | None] = mapped_column(String(10))
    msg_status: Mapped[str | None] = mapped_column(String(20))
    telco: Mapped[str | None] = mapped_column(String(10))
    done_code: Mapped[str | None] = mapped_column(String(10))
    done_desc: Mapped[str | None] = mapped_column(String(255))
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CoufunStatusCache(TimestampMixin, Base):
    __tablename__ = "coufun_status_cache"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    coupon_issue_id: Mapped[int] = mapped_column(ForeignKey("coupon_issues.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    status_source: Mapped[str] = mapped_column(String(20), nullable=False)
    status_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSON)


class EncryptionKey(TimestampMixin, Base):
    __tablename__ = "encryption_keys"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    key_alias: Mapped[str] = mapped_column(String(50), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
