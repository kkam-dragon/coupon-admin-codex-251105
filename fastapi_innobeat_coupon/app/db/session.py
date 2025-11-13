from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


# SQLAlchemy 접속 URL 생성
DATABASE_URL = (
    f"mysql+pymysql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    f"?charset=utf8mb4"
)

# 엔진 생성
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,               # 연결이 죽었는지 자동 체크
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

# 세션 팩토리
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# 의존성 주입 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
