# 기능 명세서

## 1. 사용자 및 권한
| 역할 | 주요 권한 | 비고 |
| --- | --- | --- |
| 관리자 | 사용자 관리, 발송등록/조회/CS 전체 접근, 시스템 설정 | 초기 관리자만 계정 생성 권한 보유 |
| 운영자 | 발송등록/조회/CS 접근, 쿠폰 상태 변경, 재발송 승인 | 발송 취소/재발송 시 2인 승인 옵션 지원 |
| 조회 전용 | 발송조회 화면 열람, 다운로드 | 개인정보 마스킹 상태로만 확인 |

## 2. 인증 및 보안 기능
- 로그인: 아이디+비밀번호, bcrypt 해시 검증, 5회 실패 시 계정 잠금 및 관리자 알림.
- 세션: JWT + 서버 세션 테이블 병행(`auth_sessions`), 30분 미사용 시 만료.
- 감사 로그: 로그인, 로그아웃, 조회/다운로드, 상태 변경, API 키 사용 내역을 `audit_logs`에 기록.
- 개인정보 암호화: 이름/이메일/휴대폰/쿠폰번호 AES-256-GCM, 비밀번호 bcrypt. 복호화는 권한 검사 후 서버 측에서만 수행.

## 3. 발송등록(sendCoupon.html)
### 3.1 입력 검증
- 필수 값: 고객사, 영업담당자, 이벤트명, 예약일시, 발신번호, 메시지 제목/본문, 수신자 목록, 상품.
- 문자 제한: 제목 20자, 본문 2000byte, 안내 문구 sendCoupon.html UI 기준.
- 수신자: 간편등록 최대 100건, 대량 업로드 최대 20,000건, 하이픈 제거 후 010XXXXXXXX 형식 검증.

### 3.2 상품 관리
- 공급사 상품 API(`coufunCreate`, `coufunPartAmountStatus`, `상품정보 API`)를 사용해 `coupon_products` 테이블을 매일 동기화.
- UI 검색 시 로컬 DB 캐시 사용, 가용 여부/가격 변경이 발생하면 `product_sync_logs`에 기록.

### 3.3 캠페인 저장
- 캠페인 생성 시 공통 키(`YYYYMMDDHHMISSinnobeatXXXXXXXX`)를 `campaigns.campaign_key`와 `UMS_MSG.CLIENT_KEY`에 공통 사용.
- 수신자 업로드는 `recipient_batches`(파일 메타)와 `campaign_recipients`(암호화 휴대폰, 업로드 타입)으로 저장.
- 메시지 템플릿은 `coupon_templates` 참조, 배너 업로드는 `media_assets`에 저장 후 경로만 기록.

### 3.4 예약 발송 워크플로우
1. 예약 스케줄러가 발송 10분 전에 대기 큐에 캠페인을 적재.
2. 워커가 공급사 `coufunCreate` API를 수신자당 최대 10건씩 호출하여 쿠폰번호/유효기간을 수집하고 `coupon_issues`에 암호화 저장.
3. 쿠폰번호와 메시지를 합성해 MMS 이미지를 생성(HTML 템플릿→이미지 변환). 생성 파일은 SNAP Agent 접근 경로에 저장.
4. SNAP Agent `UMS_MSG`에 캠페인/수신자별 레코드를 INSERT (`REQ_CH`=MMS, `MSG_STATUS`='ready', `MMS_FILE_LIST`에 이미지 경로).
5. 발송 결과는 `UMS_LOG_YYYYMM` 폴링 또는 콜백으로 받아 `dispatch_results`에 적재.

### 3.5 예외 처리
- 쿠폰 발행 실패 시 최대 3회 재시도, 이후 `coupon_issues.status`='ISSUE_FAILED'로 기록하고 관리자 알림.
- SNAP Agent INSERT 실패 시 재시도 큐에 저장, 5회 실패 시 캠페인 상태 'ERROR'.
- 예약 취소 시 워커 큐에서 제거하고, 발급된 쿠폰은 공급사 취소 API로 회수 후 상태 변경.

## 4. 발송조회(sendQuery.html)
- 검색 조건: 발송일 범위, 고객사명, 이벤트명. 기본 최근 7일.
- 결과 컬럼: 발송일시, 유효기간, 고객사, 이벤트, 상품, 수량, 단가, 합계, 발송상태, 상세보기, 취소처리.
- 페이징: 무한 스크롤용 cursor 기반 API (`?cursor=<last_id>&limit=50`).
- 상세 모달: 캠페인 메타, 수신자 목록(마스킹 번호), 쿠폰번호, 발송 상태, 재발송/취소 버튼.
- 엑셀 다운로드: 필터 조건 기준으로 S3/로컬에 24시간 보관 후 만료.
- 발송 취소: 예약 상태 캠페인만 가능, `UMS_MSG` 삭제 또는 `MSG_STATUS`='cancel' 처리 후 공급사 쿠폰 취소 API 호출.

## 5. CS(sendCs.html)
- 조회 조건: 쿠폰번호(마스킹 입력 허용), 휴대폰 번호.
- 응답: 쿠폰 상태(미교환/교환/폐기/재사용 가능), 만료 여부, 교환일시, 취소일시, 잔액.
- CS 처리 액션:
  - **재발송**: 기존 캠페인 참조, 새 `CLIENT_KEY` 생성하여 SNAP Agent에 재등록, `cs_actions`에 기록.
  - **번호 변경**: 수신자 정보 업데이트 후 공급사에 변경 요청(필요 시 취소 후 재발급), `campaign_recipients` 히스토리 남김.
  - **쿠폰 폐기**: 공급사 취소 API 호출, `coupon_issues.status`='CANCELLED', CS 사유 기록.
  - **기타 메모**: 자유 형식 메모, 감사 로그와 연동.
- 상태 조회는 공급사 `coufunPartAmountStatus` API와 내부 `coupon_status_history`를 조합하여 최신 정보 제공.

## 6. 파일/이미지 관리
- 배너 업로드: 바이러스 검사 후 `media_assets`에 저장, 원본과 썸네일 경로 기록.
- MMS 쿠폰 이미지: 예약 워커에서 `rendered_mms` 디렉터리에 저장, 파일명은 `CLIENT_KEY_page#.jpg` 규칙 적용.
- SNAP Agent 공유: 카페24 VPS 내 SNAP Agent 설치 경로에 symlink 또는 NFS 마운트.

## 7. 관리 도구
- 상품 동기화 스케줄러: 매일 04:00 실행, 변경 내역 Slack/Webhook 알림.
- 쿠폰 상태 동기화: 5분 간격 배치로 공급사 상태 조회, `coupon_status_history` 업데이트.
- 발송 모니터링: 예약 큐, 발송 성공률, 실패 사유 통계 대시보드.

## 8. 비기능 요구사항
- 성능: 20,000건 발송을 30분 내로 SNAP Agent 큐에 적재.
- 가용성: 예약 워커 중단 시 알람, 재시작 자동화(systemd).
- 보안: HTTPS, DB 접근 IP 제한, 민감 로그 마스킹, 개인정보 파기 정책(90일 주기).
- 감사: 모든 상태 변경은 CS/운영자 아이디와 함께 기록, 보고서 CSV 제공.