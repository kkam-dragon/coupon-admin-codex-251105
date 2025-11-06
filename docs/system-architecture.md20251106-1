# 시스템 아키텍처

## 1. 개요
본 문서는 모바일 쿠폰 백오피스의 전체 기술 구성을 정의한다. 아키텍처는 Python 3.11 + FastAPI 기반 백엔드, MariaDB 10.x 데이터베이스, SNAP Agent 및 COUFUN API 연동을 중심으로 설계된다.

## 2. 논리 아키텍처
```mermaid
graph TD
    A[사용자 브라우저] --> B[정적 프런트엔드 (HTML/CSS/JS)]
    B --> C[FastAPI 백엔드 서비스]
    C --> D[(MariaDB 10.x)]
    C --> E[Redis (옵션)]
    C --> F[파일 스토리지/NAS]
    C --> G[COUFUN B2C API]
    C --> H[LG U+ SNAP Agent]
    H --> I[UMS_MSG / UMS_LOG]
```

## 3. 물리 아키텍처
| 계층 | 구성 요소 | 비고 |
| --- | --- | --- |
| 프런트엔드 | 기존 HTML/JS (Bootstrap, Flatpickr) | GitHub에 정적 배포, 로컬 테스트는 파일 직접 오픈 |
| 백엔드 | FastAPI + Uvicorn + Gunicorn, Python 3.11 | Docker Compose 로컬 실행, 카페24 VPS systemd 서비스 |
| 데이터베이스 | MariaDB 10.x | Docker 내 또는 카페24 VPS 내 별도 서비스, 연결 포트 3306 |
| 캐시/큐 | Redis 7 (선택) | 예약 발송 큐, 작업 잠금, 세션 캐시 |
| 외부 서비스 | COUFUN B2C API, LG유플러스 SNAP Agent | IP 화이트리스트 필요, HTTPS 호출 |
| 파일 스토리지 | 로컬 디스크 + SNAP Agent 공유 경로 | MMS 이미지, 배너 자산 저장 |

## 4. 백엔드 서비스 구성
- **API 계층**: FastAPI로 RESTful 엔드포인트 제공, Swagger UI 자동 문서화.
- **비즈니스 계층**: 서비스 모듈에서 캠페인 생성, 쿠폰 발행, 상태 동기화 로직 구현.
- **데이터 계층**: SQLAlchemy + Alembic으로 ORM/마이그레이션 관리. 암호화 컬럼은 커스텀 타입으로 구현.
- **배치/워커**: APScheduler 기반 예약 작업 + 백그라운드 워커(비동기 태스크 또는 Celery). 예약 발송, 상품 동기화, 상태 동기화 담당.
- **이미지 렌더러**: Playwright headless 또는 WeasyPrint/Pillow를 활용한 HTML→이미지 변환 서비스. Docker 컨테이너에서 추가 패키지 설치.

## 5. 통합 포인트
### 5.1 COUFUN API
- 상품 정보: `b2c_api/coufunGoods.do` (문서 1 참조) → `coupon_products` 갱신.
- 쿠폰 생성: `b2c_api/coufunCreate.do` (문서 2 참조) → 수신자당 최대 10건 발급.
- 쿠폰 취소: `b2c_api/coufunCancel.do` (문서 4 참조) → 발송 취소/CS 폐기 시 호출.
- 쿠폰 상태조회: `b2c_api/coufunPartAmountStatus.do` (문서 3 참조) → 교환/잔액 확인.
- 교환 정보 수집: `b2c_api/coufunExchangeInfo.do` (문서 5 참조) → 교환 매장, 일시, 상태 업데이트.

### 5.2 LG유플러스 SNAP Agent
- MMS 발송: `UMS_MSG` 테이블 INSERT (`REQ_CH`='MMS', `MSG_STATUS`='ready', `MMS_FILE_LIST` 규칙). (문서 2-1, 2-2 참조)
- 발송 결과: `UMS_LOG_YYYYMM` 테이블 폴링 + `DONE_CODE`, `DONE_CODE_DESC` 분석 (문서 3, 4 참조).
- 이미지 저장: SNAP Agent 홈의 `yyyymmdd` 디렉터리 및 `MSGHUB_IMG` 테이블 자동 등록.

## 6. 인프라 다이어그램
```mermaid
graph LR
    subgraph 로컬/개발 환경
        DevPC[개발자 PC]
        DevPC -->|Git Clone| Repo[(GitHub Repository)]
        DevPC -->|Docker Compose| FastAPI
        FastAPI --> MariaDB
        FastAPI --> Redis
    end

    subgraph 운영 환경 (Cafe24 VPS)
        Nginx --> Gunicorn
        Gunicorn --> FastAPI_Prod[(FastAPI 서비스)]
        FastAPI_Prod --> MariaDB_Prod[(MariaDB)]
        FastAPI_Prod --> Redis_Prod[(Redis)]
        FastAPI_Prod --> SNAP[SNAP Agent]
        SNAP --> LGUCloud[LG U+ Message Hub]
        FastAPI_Prod --> COUFUN[COUFUN API]
    end

    Repo -->|CI/CD| Nginx
```

## 7. 보안 아키텍처
- **네트워크**: 카페24 방화벽에서 80/443, 22, 3306 제한. SNAP Agent/COUFUN 허용 IP만 오픈.
- **암호화 키 관리**: 환경 변수 + Vault(선택). 키 변경 시 `encryption_keys` 테이블에 버전 기록.
- **인증/인가**: JWT 서명 키 관리, RBAC 미들웨어로 API 접근 제어.
- **로그**: 구조화 로그(JSON), 개인정보 마스킹, ELK 또는 Loki 스택 연동 선택.

## 8. 고가용성 및 확장 고려
- FastAPI 서비스는 Gunicorn 다중 워커로 운영, 필요 시 수평 확장(추가 VPS) 가능.
- MariaDB는 주기적 백업 + 복구 테스트, 장기적으로는 MariaDB Galera 또는 RDS 고려.
- Redis는 세션/락 관리 용도로 사용하며, 다운 시 fallback 전략 수립.
- 워커는 systemd 서비스로 등록, 장애 발생 시 자동 재시작 및 Slack 알림.