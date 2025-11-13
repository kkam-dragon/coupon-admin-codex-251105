# 1️⃣ Python 3.11 slim 버전 기반 이미지
FROM python:3.11-slim

# 2️⃣ 작업 디렉토리 설정
WORKDIR /app

# 3️⃣ requirements.txt 복사
COPY requirements.txt .

# 4️⃣ 필요한 패키지 미리 설치 (bake-in)
RUN pip install --no-cache-dir -r requirements.txt

# 5️⃣ FastAPI 앱 복사
COPY . .

# 6️⃣ 컨테이너 실행 시 FastAPI 서버 실행
# 개발서버용으로는 부적합 > CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]
