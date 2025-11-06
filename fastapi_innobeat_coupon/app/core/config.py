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

    model_config = SettingsConfigDict(
        env_file=(".env", ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def encryption_key_bytes(self) -> bytes:
        return bytes.fromhex(self.encryption_key)


settings = Settings()
