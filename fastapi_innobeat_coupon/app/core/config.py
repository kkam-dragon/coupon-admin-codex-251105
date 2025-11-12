from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Coupon Admin API", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")

    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=3306, alias="DB_PORT")
    db_user: str = Field(default="coupon_user", alias="DB_USER")
    db_password: str = Field(default="coupon_pass", alias="DB_PASSWORD")
    db_name: str = Field(default="innobeat_coupon_db", alias="DB_NAME")
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=5, alias="DB_MAX_OVERFLOW")
    encryption_key: str = Field(
        default="0123456789abcdeffedcba98765432100123456789abcdeffedcba9876543210",
        alias="ENCRYPTION_KEY",
    )
    snap_traffic_type: str = Field(default="normal", alias="SNAP_TRAFFIC_TYPE")
    snap_req_channel: str = Field(default="MMS", alias="SNAP_REQ_CHANNEL")
    snap_req_dept_code: str | None = Field(default=None, alias="SNAP_REQ_DEPT_CODE")
    snap_req_user_id: str | None = Field(default=None, alias="SNAP_REQ_USER_ID")
    snap_sync_enabled: bool = Field(default=True, alias="SNAP_SYNC_ENABLED")
    snap_sync_interval_seconds: int = Field(default=180, alias="SNAP_SYNC_INTERVAL_SECONDS")
    snap_sync_lookback_minutes: int = Field(default=60, alias="SNAP_SYNC_LOOKBACK_MINUTES")
    product_sync_enabled: bool = Field(default=True, alias="PRODUCT_SYNC_ENABLED")
    product_sync_hour_utc: int = Field(default=19, alias="PRODUCT_SYNC_HOUR_UTC")
    coupon_status_sync_enabled: bool = Field(default=True, alias="COUPON_STATUS_SYNC_ENABLED")
    coupon_status_sync_interval_seconds: int = Field(
        default=300,
        alias="COUPON_STATUS_SYNC_INTERVAL_SECONDS",
    )
    coupon_status_sync_batch_size: int = Field(
        default=200,
        alias="COUPON_STATUS_SYNC_BATCH_SIZE",
    )
    virus_scan_enabled: bool = Field(default=False, alias="VIRUS_SCAN_ENABLED")
    virus_scan_command: str | None = Field(default=None, alias="VIRUS_SCAN_COMMAND")
    send_query_export_dir: str = Field(
        default="temp/exports/send_query",
        alias="SEND_QUERY_EXPORT_DIR",
    )
    send_query_export_ttl_hours: int = Field(
        default=24,
        alias="SEND_QUERY_EXPORT_TTL_HOURS",
    )
    export_cleanup_enabled: bool = Field(default=True, alias="EXPORT_CLEANUP_ENABLED")
    export_cleanup_interval_minutes: int = Field(
        default=60,
        alias="EXPORT_CLEANUP_INTERVAL_MINUTES",
    )
    coufun_base_url: str | None = Field(default=None, alias="COUFUN_BASE_URL")
    coufun_poc_id: str | None = Field(default=None, alias="COUFUN_POC_ID")
    coufun_timeout: float = Field(default=10.0, alias="COUFUN_TIMEOUT")
    coufun_mock_mode: bool = Field(default=True, alias="COUFUN_MOCK_MODE")
    jwt_secret_key: str = Field(default="coupon-admin-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    model_config = SettingsConfigDict(
        env_file=(".env", ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def encryption_key_bytes(self) -> bytes:
        return bytes.fromhex(self.encryption_key)


settings = Settings()
