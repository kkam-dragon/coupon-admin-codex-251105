# 데이터 모델 명세

## 1. 설계 원칙
- 개인정보 및 중요정보는 AES-256-GCM으로 암호화하고, 해시/마스킹을 병행한다.
- 모든 주요 테이블은 공통 키(`client_key`)를 참조하여 SNAP Agent, COUFUN, 내부 시스템 간 추적을 용이하게 한다.
- 생성/수정/삭제 시 `created_at`, `updated_at`, `created_by`, `updated_by`를 공통 컬럼으로 유지한다.
- 상태 값은 코드 테이블(`code_groups`, `code_items`)로 관리하며, 공급사 코드 표(`6.COUFUN_B2C_코드정의서_연동매뉴얼.md`)와 매핑한다.

## 2. 핵심 엔터티
### 2.1 사용자 및 권한
| 테이블 | 주요 컬럼 | 설명 |
| --- | --- | --- |
| `users` | `id`, `username`, `password_hash`, `enc_name`, `enc_email`, `enc_phone`, `status`, `last_login_at` | 비밀번호는 bcrypt, 개인정보 컬럼은 AES 암호화 |
| `roles` | `id`, `code`, `name`, `description` | 관리자/운영자/조회전용 등 |
| `user_roles` | `user_id`, `role_id` | 다대다 매핑 |
| `auth_sessions` | `id`, `user_id`, `jwt_id`, `expires_at`, `ip_address`, `user_agent` | 세션 관리 |

### 2.2 고객/캠페인
| 테이블 | 주요 컬럼 | 설명 |
| --- | --- | --- |
| `clients` | `id`, `name`, `enc_contact_name`, `enc_contact_phone`, `enc_contact_email`, `sales_manager_id`, `status` | 고객사 기본 정보 |
| `campaigns` | `id`, `campaign_key`, `client_id`, `event_name`, `scheduled_at`, `sender_number`, `message_title`, `message_body`, `banner_asset_id`, `status` | 발송 캠페인 기본 정보 |
| `campaign_status_logs` | `id`, `campaign_id`, `status`, `detail`, `logged_at`, `logged_by` | 상태 변경 이력 |
| `campaign_products` | `id`, `campaign_id`, `coupon_product_id`, `unit_price`, `settle_price` | 선택된 상품 정보 |

### 2.3 수신자 및 배치
| 테이블 | 주요 컬럼 | 설명 |
| --- | --- | --- |
| `recipient_batches` | `id`, `campaign_id`, `upload_type`, `original_filename`, `total_count`, `valid_count`, `invalid_count`, `uploaded_by` | 간편등록/엑셀 업로드 메타 |
| `campaign_recipients` | `id`, `campaign_id`, `batch_id`, `enc_phone`, `enc_name`, `status`, `validation_error`, `created_at` | 수신자별 상태 (PENDING/VALID/INVALID/SENT 등) |
| `recipient_histories` | `id`, `recipient_id`, `action`, `old_value`, `new_value`, `created_by`, `created_at` | 휴대폰 번호 변경 등 추적 |

### 2.4 쿠폰 및 이력
| 테이블 | 주요 컬럼 | 설명 |
| --- | --- | --- |
| `coupon_products` | `id`, `goods_id`, `name`, `face_value`, `purchase_price`, `valid_days`, `vendor_status`, `last_synced_at` | 공급사 상품 정보, `goods_id` 유니크 |
| `coupon_issues` | `id`, `campaign_id`, `recipient_id`, `order_id`, `barcode_enc`, `valid_end_date`, `status`, `vendor_payload`, `issued_at` | 쿠폰 발급 결과, 바코드 암호화 저장 |
| `coupon_status_history` | `id`, `coupon_issue_id`, `status`, `status_source`, `status_at`, `memo` | 공급사 push/poll 결과, CS 처리 이력 |
| `coupon_exchange_details` | `id`, `coupon_issue_id`, `exchange_store`, `exchange_at`, `cancel_at`, `remain_amount` | 문서 5의 교환 정보 API 대응 |

### 2.5 발송/결과
| 테이블 | 주요 컬럼 | 설명 |
| --- | --- | --- |
| `mms_jobs` | `id`, `campaign_id`, `recipient_id`, `client_key`, `ums_msg_id`, `req_date`, `status`, `retry_count` | SNAP Agent INSERT 결과 추적 |
| `dispatch_results` | `id`, `mms_job_id`, `done_code`, `done_desc`, `telco`, `sent_at`, `completed_at` | UMS_LOG 연동 결과 |
| `rendered_assets` | `id`, `campaign_id`, `recipient_id`, `file_path`, `file_hash`, `created_at` | 생성된 MMS 이미지 파일 |

### 2.6 CS 및 감사
| 테이블 | 주요 컬럼 | 설명 |
| --- | --- | --- |
| `cs_actions` | `id`, `coupon_issue_id`, `recipient_id`, `action_type`, `reason`, `performed_by`, `performed_at`, `result_status` | 재발송, 폐기, 번호 변경 등 |
| `audit_logs` | `id`, `user_id`, `action`, `target_type`, `target_id`, `ip_address`, `user_agent`, `created_at`, `success` | 접근/변경 감사 |
| `encryption_keys` | `id`, `version`, `key_alias`, `rotated_at`, `status` | 키 교체 이력 (옵션) |

## 3. 데이터 흐름
1. **캠페인 생성**: `campaigns` + `campaign_products` + `campaign_recipients` INSERT → 상태 `DRAFT`.
2. **예약 승인**: `campaigns.status` `SCHEDULED`로 변경, `campaign_status_logs` 기록.
3. **쿠폰 발급**: 워커가 `coupon_issues` INSERT, `coupon_status_history`에 `ISSUED` 기록.
4. **MMS 요청**: `mms_jobs` INSERT → SNAP Agent `UMS_MSG` → 결과 `dispatch_results`.
5. **CS 처리**: `cs_actions` INSERT, 필요 시 `coupon_issues.status` 업데이트, 공급사 API 호출 결과를 `coupon_status_history`에 추가.

## 4. 암호화/마스킹 정책
- AES 컬럼: `enc_phone`, `enc_email`, `enc_name`, `barcode_enc`.
- 마스킹 뷰: `vw_recipients_masked`, `vw_coupons_masked` 등 뷰 생성하여 화면에는 `010-****-1234` 형식으로 제공.
- 키 관리: 환경 변수로 AES 키/IV를 관리하고, `encryption_keys` 버전과 매핑.

## 5. 코드/상태 정의
| 코드 그룹 | 값 | 설명 |
| --- | --- | --- |
| `campaign_status` | DRAFT, SCHEDULED, ISSUING, SENDING, COMPLETED, ERROR, CANCELLED | 캠페인 진행 상태 |
| `coupon_status` | ISSUED, SENT, DELIVERED, USED, CANCELLED, REUSABLE, EXPIRED, ISSUE_FAILED | 쿠폰 상태 (공급사 코드 매핑) |
| `recipient_status` | PENDING, VALIDATED, INVALID, SENT, FAILED | 수신자 상태 |
| `cs_action_type` | RESEND, CHANGE_PHONE, CANCEL_COUPON, NOTE | CS 처리 유형 |

## 6. 인덱스 및 성능 전략
- `campaign_recipients`: `(campaign_id, status)`, `(enc_phone_hash)` (SHA-256 해시 컬럼) 인덱스.
- `coupon_issues`: `(campaign_id, status)`, `(order_id)`, `(valid_end_date)`.
- `dispatch_results`: `(done_code)`, `(completed_at)` 인덱스로 통계 쿼리 최적화.
- 파티셔닝: `dispatch_results`, `coupon_status_history`는 월 단위 파티션 고려.

## 7. 데이터 보존 정책
- 발송/쿠폰 로그: 2년 보관, 이후 비식별화 후 아카이브.
- 엑셀 원본: 7일 후 자동 삭제.
- 감사 로그: 5년 보관.