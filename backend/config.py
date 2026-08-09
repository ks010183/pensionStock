"""공통 설정."""
import os

DB_HOST = os.getenv("ETF_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("ETF_DB_PORT", "3306"))
DB_USER = os.getenv("ETF_DB_USER", "etf")
DB_PASSWORD = os.getenv("ETF_DB_PASSWORD", "etf1234")
DB_NAME = os.getenv("ETF_DB_NAME", "etf_db")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

# ---------------------------------------------------------------------------
# LLM 설정 — 멀티 프로바이더 (anthropic / openai / gemini)
# ---------------------------------------------------------------------------
# API 키: 설정된 키가 있는 프로바이더만 사용 가능
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCXXllaVmB94nDVToBqermfNc9sqo1AsL4") or os.getenv("GOOGLE_API_KEY", "")

# 전역 기본 프로바이더: auto | anthropic | openai | gemini | none
#   auto = 키가 설정된 첫 번째 프로바이더 자동 선택 (anthropic → openai → gemini)
#   none = LLM 미사용 (모든 Agent 규칙기반)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "")          # 전역 모델 오버라이드 (선택)

# Agent 별 프로바이더/모델 오버라이드. 형식: "provider" 또는 "provider:model"
#   예) AGENT_LLM_INPUT=openai:gpt-5.4-mini  AGENT_LLM_EVALUATION=gemini
# 키: INPUT(입력분석) ACCOUNT(계좌분석) SEARCH(검색) OPTIMIZATION(최적화) EVALUATION(평가)
AGENT_LLM_OVERRIDES = {
    key: os.getenv(f"AGENT_LLM_{key}", "").strip()
    for key in ("INPUT", "ACCOUNT", "SEARCH", "OPTIMIZATION", "EVALUATION")
}

# 퇴직연금 위험자산 한도 (총 평가금액 대비)
PENSION_RISK_LIMIT = 0.70

# ---------------------------------------------------------------------------
# 실제 DB(etf_integration 등) 기반 ETF 유니버스/분류 규칙
# ---------------------------------------------------------------------------
# 연금 매매가능 필터: etf_integration.pension 값이 비어있지 않은 상품만 사용
UNIVERSE_REQUIRE_PENSION = os.getenv("UNIVERSE_REQUIRE_PENSION", "1") == "1"

# 안전자산(SAFE) 분류 규칙 — fund_type 이 아래 목록이거나, 상품명/벤치마크/키워드에
# 아래 키워드가 포함되면 SAFE, 그 외는 RISK.
# 실제 값 분포 확인 후 조정 가능: SELECT fund_type, COUNT(*) FROM etf_integration GROUP BY fund_type;
SAFE_FUND_TYPES = [
    s.strip() for s in os.getenv(
        "SAFE_FUND_TYPES", "채권형,단기금융,금리형,채권혼합형,혼합채권형"
    ).split(",") if s.strip()
]
SAFE_NAME_KEYWORDS = [
    s.strip() for s in os.getenv(
        "SAFE_NAME_KEYWORDS",
        "채권,국고채,국공채,회사채,단기채,종합채,금리,KOFR,CD금리,머니마켓,MMF,단기자금,통안,TDF2025",
    ).split(",") if s.strip()
]

# 최적화 후보에 항상 포함할 안전자산 ETF 최대 개수 (시총 상위)
MAX_SAFE_CANDIDATES = int(os.getenv("MAX_SAFE_CANDIDATES", "10"))
