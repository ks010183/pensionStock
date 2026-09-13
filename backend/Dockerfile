# ---- 백엔드 (FastAPI + 멀티 Agent + MCP 서버) ----
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend

EXPOSE 8000

# MCP 서버는 검색Agent가 stdio 서브프로세스로 자동 기동 (동일 컨테이너 내부)
# Railway 등 PaaS 는 PORT 환경변수로 포트를 지정한다 (로컬은 기본 8000)
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
