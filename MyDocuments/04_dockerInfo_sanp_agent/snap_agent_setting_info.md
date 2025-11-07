# SNAP Agent 설치 및 연동 정보

## 1. 접속 방식
- **OS / 위치** : Ubuntu 20.04 (Docker 환경, 로컬 개발서버)  
- **호스트명/IP** : `innobeat-dev.local / 192.168.xxx.xxx`  
- **접속 포트** : SSH 22 (내부망), Docker Port 8089(FastAPI), 3307(MariaDB)  
- **접근 계정** : `root` 또는 `innobeat` 계정 / Docker 컨테이너 내 `root` 사용  

---

## 2. DB / 연동 경로
- **DB 종류** : MariaDB 11.3 (로컬 Docker 컨테이너)  
- **DB 명** : `innobeat_coupon_db`  
- **사용자** : `coupon_user / coupon_pass`  
- **포트** : 3307 → (내부 3306 매핑)  
- **연동 상태** : SNAP Agent 테이블 자동 생성 완료 (`SC_TRAN`, `MMS_MSG`, `UMS_MSG` 등)  
- **DB 권한** : `CREATE`, `ALTER`, `INDEX`, `SELECT`, `INSERT`, `UPDATE`, `DELETE`

---

## 3. 메시지 큐 / 로그 저장 위치
- **메시지 큐** : SNAP 내부 QueueManager 자동 구성  
  - `send-ums-ums-normal-msghub`  
  - `result-ums-ums-normal`  
  - `report-ums-ums-normal` 등  
- **로그 파일** : `/app/log/` (호스트 경로 → `D:\_Docker_data\03_snap_agent\log\`)  
  - 주요 로그: `snap.log`, `snap.out`, `snap.err`  
  - 로그 로테이션: Docker json 로그 10 MB × 5 파일 제한  

---

## 4. 보안 키 / 토큰
- **API Key (ID)** : `APIXKgpN`  
- **API Password** : (비공개 / LG U+ 발급 운영용 비밀번호)  
- **토큰 상태** : Auth 성공 (`Auth success. ID=APIXKgpN`, HealthCheck=성공)  
- **전달 방식** : 보안 채널 (암호화 이메일 또는 VPN 내 공유) 로만 전달 가능  

---

## 5. 운영 절차
- **기동** :  
  ```bash
  docker start snap_agent
