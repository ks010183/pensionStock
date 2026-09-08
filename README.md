# 연금 ETF 포트폴리오 최적화 (pensionStock)

고객의 희망 종목 포트폴리오(예: 삼성전자 20%, 현대차 10%, 한화 20%)에 대해,
현재 계좌의 보유 ETF·현금을 고려하여 **어떤 ETF를 얼마나 추가 매수하면
종목 노출이 목표에 가장 가까워지는가**를 멀티 Agent + MCP 구조로 풀어주는
시스템입니다.

## 아키텍처

```
┌────────────────────────── 모바일 프론트 (React + Vite) ─────────────────────────┐
│  입력 화면 → 추천결과 → 유사종목(MCP) → Agent 로그    (max-width 430px)          │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │ REST (/api/recommend)
┌──────────────────────────────────▼──────────────────────────────────────────────┐
│  FastAPI 백엔드 — 멀티 Agent 오케스트레이터                                       │
│                                                                                  │
│  입력분석Agent ─► 계좌분석Agent ─► 검색Agent ─► 최적화Agent ─► 평가Agent          │
│   (LLM/규칙 파싱)  (룩스루 노출)    (MCP 클라이언트)  (QP, SLSQP)  (실행가능성)      │
│                                      │ stdio                                     │
│                            ┌─────────▼──────────┐                                │
│                            │  ETF DB MCP 서버    │  도구 3종:                     │
│                            │  (FastMCP, stdio)  │  · etfs_containing_stock       │
│                            └─────────┬──────────┘  · stocks_in_same_sector       │
│                                      │             · stocks_in_same_theme        │
└──────────────────────────────────────┼──────────────────────────────────────────┘
                             ┌─────────▼──────────┐
                             │  MySQL (etf_db)    │  기본/구성종목/테마/섹터/국가    │
                             └────────────────────┘
```

### 멀티 Agent 역할

| Agent | 역할 |
|---|---|
| 입력분석Agent | 희망 포트폴리오 텍스트를 상세화 분석 → `{종목코드: 목표비중%}` 정규화. 배정된 LLM으로 파싱, 없으면 규칙기반 |
| 계좌분석Agent | 보유 ETF 룩스루(look-through) 분석 → 종목별 노출 합계·위험자산 비중·계좌 총액 |
| 검색Agent | **MCP 클라이언트**로 ETF DB MCP 서버에 접속 → 목표 종목 포함 ETF 랭킹, 동일 섹터/테마 유사 종목 검색 |
| 최적화Agent | 앞의 두 Agent 출력을 받아 QP 최적화 실행 → 유사도 기준 추천 ETF 랭킹 |
| 평가Agent | 현금 한도·퇴직연금 70% 규정·수렴 여부·개선 효과를 검증 → EXECUTABLE / CONDITIONAL / REJECTED. 배정된 LLM으로 종합의견 생성 |

### Agent 별 LLM 프로바이더 (anthropic / openai / gemini)

각 Agent 는 **서로 다른 LLM 프로바이더·모델**을 배정받을 수 있습니다.
API 키가 하나도 없으면 전체가 규칙기반으로 동작합니다 (LLM 은 항상 선택사항).

```bash
# API 키 (설정된 것만 사용 가능)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...          # 또는 GOOGLE_API_KEY

# 전역 기본: auto(키 있는 첫 프로바이더) | anthropic | openai | gemini | none
LLM_PROVIDER=auto
LLM_MODEL=                       # 전역 모델 오버라이드 (선택)

# Agent 별 오버라이드 — "provider" 또는 "provider:model"
AGENT_LLM_INPUT=openai:gpt-5.4-mini          # 입력분석: 자유 텍스트 파싱
AGENT_LLM_EVALUATION=gemini:gemini-3.6-flash # 평가: 종합의견 생성
AGENT_LLM_ACCOUNT=anthropic                  # 계좌분석: 요약 (명시 시에만 호출)
AGENT_LLM_SEARCH=openai                      # 검색: 요약 (명시 시에만 호출)
AGENT_LLM_OPTIMIZATION=anthropic             # 최적화: 배분 설명 (명시 시에만 호출)
```

- 기본 모델: anthropic `claude-sonnet-5`, openai `gpt-5.4-mini`, gemini `gemini-3.6-flash`
- 입력분석·평가는 전역 설정만으로도 LLM을 사용하고, 계좌분석·검색·최적화의
  보조 코멘트는 파이프라인 지연을 피하기 위해 **해당 Agent에 명시했을 때만** 호출됩니다.
- LLM 호출이 실패하면 해당 Agent 는 자동으로 규칙기반/생략으로 폴백하며,
  사용된 프로바이더와 폴백 여부는 Agent 로그(trace)에 기록됩니다.

### 최적화 알고리즘 (왜 QP인가)

- 결정변수 `x_j ≥ 0` : 후보 ETF j 의 추가 매수금액
- 목적함수 : `min Σ_s ( (기존노출_s + Σ_j x_j·w_js)/계좌총액 − 목표_s )²`
- 제약 : ① `Σx ≤ 현금` ② 퇴직연금이면 `위험자산 총액 ≤ 0.7 × 계좌총액` ③ `x ≥ 0`

목적함수가 볼록 이차식 + 선형 제약 → **볼록 QP**로 전역 최적해가 보장되며,
scipy **SLSQP**(해석적 gradient 제공)로 수십 개 변수를 밀리초 단위에 풉니다.
1주 단위 정수화는 "내림 후 그리디 보정" 2단계 휴리스틱으로 처리합니다
(오차가 1주 가격 수준이라 실무적으로 충분).

## 데이터: 실제 ETF DB 사용

백엔드는 **실제 ETF DB**(별도 MySQL 컨테이너, root/mysql, DB=etf_db)의 4개 테이블을
사용합니다 — 상세 스키마: `db/REAL_DB_SCHEMA.md`

| 테이블 | 용도 |
|---|---|
| `etf_integration` | ETF 기본 (연금가능 `pension`, 보수, NAV/이동평균가, 시총) |
| `datamart_etfholderkor` | 구성종목 (`asset`=종목티커, `item_name`=종목명, `weight_percentage`) |
| `datamart_etfsectorweightkor` | ETF 단위 섹터 비중 (종목 섹터는 편입 ETF 가중합으로 추정) |
| `datamart_stockcategorykor` | 테마 (테마→심볼 매핑, `search_tag` 키워드) |

ETF 유니버스 필터: `status='active'` + ETF 타입 + `pension` 값 존재 + 비레버리지/비인버스.
RISK/SAFE 분류: `fund_type`(채권형 등) 또는 상품명/벤치마크/키워드 규칙
(`SAFE_FUND_TYPES`/`SAFE_NAME_KEYWORDS` env 로 조정). 가격은 10일 이동평균가→NAV 근사.
분류 규칙 검증: `./db/inspect_values.sh` 실행 후 `db/values_dump.txt` 의 값 분포 확인.

> 실제 DB 없이 개발/테스트하려면 `db/dev_seed_real_schema.sql` 로
> 동일 구조의 샘플 테이블을 만들 수 있습니다.
> (기존 데모 스키마 `db/schema.sql`·`seed.sql` 은 참고용으로만 남아 있습니다)

## 실행 방법 A — Docker (권장, 한 번에 기동)

전제: 실제 etf_db MySQL 컨테이너가 로컬에서 실행 중 (포트 3306 공개).

```bash
docker compose up -d --build
```

| 서비스 | 주소 | 설명 |
|---|---|---|
| frontend | http://localhost:8080 | 모바일 웹 (nginx가 `/api`를 backend로 프록시) |
| backend | http://localhost:8000 | FastAPI — `host.docker.internal:3306` 의 실제 DB 접속 |

- 백엔드는 실행 중인 실제 MySQL 에 접속하므로 별도 DB 컨테이너를 띄우지 않습니다.
- DB 접속 정보 변경: `docker-compose.yml` 의 `ETF_DB_*` 환경변수.
- LLM 파싱을 켜려면 backend 환경변수에 API 키를 넣으세요 (아래 LLM 섹션).
- 모바일 시뮬레이션: 크롬 개발자도구(F12) → 기기 툴바(Ctrl+Shift+M).

### 트러블슈팅

- **추천 클릭 시 500 에러**: `curl http://localhost:8000/api/health/db` 로 DB 연결을
  먼저 확인하세요. 전체 트레이스백은 `docker compose logs backend` 에 남습니다.
- MySQL 8의 `caching_sha2_password` 인증에는 `cryptography` 패키지가 필요합니다
  (requirements.txt 에 포함됨). 코드 수정 후에는 반드시
  `docker compose up -d --build backend` 로 이미지를 다시 빌드하세요.

## 실행 방법 B — 로컬 직접 실행

### 1) DB — 실제 etf_db MySQL 이 떠 있으면 그대로 사용

```bash
export ETF_DB_HOST=127.0.0.1 ETF_DB_USER=root ETF_DB_PASSWORD=mysql ETF_DB_NAME=etf_db
```

> 실제 DB 가 없는 개발 환경: `mysql --default-character-set=utf8mb4 -u root < db/dev_seed_real_schema.sql`
> ⚠️ SQL 로드 시 반드시 `--default-character-set=utf8mb4` (한글 인코딩).

### 2) 백엔드

```bash
pip install -r backend/requirements.txt
# (선택) LLM 파싱을 쓰려면: export ANTHROPIC_API_KEY=sk-ant-...
uvicorn backend.main:app --reload --port 8000
```

MCP 서버는 검색Agent가 요청 시 stdio 서브프로세스로 자동 기동하므로 따로 띄울
필요가 없습니다. 단독 실행/테스트: `python backend/mcp_server/etf_mcp_server.py`

### 3) 프론트 (모바일 화면)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (/api → :8000 프록시)
```

**모바일 시뮬레이션**: 크롬 개발자도구(F12) → 기기 툴바(Ctrl+Shift+M) →
iPhone/Galaxy 프리셋 선택. 화면은 max-width 430px 모바일 우선으로 설계되어
데스크톱 브라우저에서도 폰 프레임 형태로 표시됩니다. 다크모드 자동 대응.

## API

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/etfs` | 전체 ETF 목록 |
| GET | `/api/stocks/search?q=` | 종목 검색 |
| POST | `/api/recommend` | 멀티 Agent 파이프라인 실행 |

```json
POST /api/recommend
{
  "desired_portfolio": "삼성전자 20%, 현대차 10%, 한화 20%",
  "account": {
    "account_type": "pension",          // pension(퇴직연금) | personal(개인연금)
    "cash": 7000000,
    "holdings": [{ "etf_code": "069500", "amount": 3000000 }]
  }
}
```

## DB 스키마

- `countries` 국가 / `sectors` 섹터 / `themes` 테마
- `stocks` 주식종목 (+ `stock_themes` M:N)
- `etfs` ETF 기본 (asset_class: RISK/SAFE, close_price, 총보수 등)
- `etf_holdings` ETF 구성종목·비중

시드 데이터는 데모용 근사치입니다. 실서비스에서는 운용사 PDF(Portfolio
Deposit File) 또는 데이터 벤더 피드로 `etfs`/`etf_holdings`를 일 배치 갱신하는
것을 전제로 합니다.

## 프로젝트 구조

```
pensionStock/
├── db/                      # schema.sql, seed.sql
├── docker-compose.yml       # db + backend + frontend 전체 스택
├── backend/
│   ├── Dockerfile
│   ├── main.py              # FastAPI 엔트리포인트
│   ├── config.py            # DB/LLM 설정
│   ├── database.py          # SQL 함수 (MCP·Agent 공용)
│   ├── optimizer/engine.py  # QP 최적화 엔진 (SLSQP + 그리디 정수화)
│   ├── agents/              # 5개 Agent + 오케스트레이터
│   └── mcp_server/etf_mcp_server.py   # FastMCP stdio 서버 (도구 3종)
└── frontend/                # React + Vite 모바일 UI
    ├── Dockerfile           # node 빌드 → nginx 서빙 (멀티 스테이지)
    └── nginx.conf           # SPA 라우팅 + /api 프록시
```

## API 키 관리 및 Railway 배포

**비밀값(API 키)은 코드/compose 파일에 절대 쓰지 않습니다** — 저장소에 커밋되는 순간 유출됩니다.

### 로컬 PC

```bash
cp .env.example .env     # 템플릿 복사
# .env 를 열어 실제 키 입력 (.env 는 gitignore 되어 커밋되지 않음)
docker compose up -d --build
```

- `docker compose` 는 프로젝트 루트의 `.env` 를 자동으로 읽어 `${VAR}` 를 치환합니다.
- `uvicorn` 직접 실행 시에도 `backend/config.py` 의 `load_dotenv()` 가 `.env` 를 읽습니다.

### Railway

Railway 대시보드 → 해당 서비스 → **Variables** 탭에 `.env.example` 과 같은 이름으로 등록합니다
(`GEMINI_API_KEY`, `LLM_PROVIDER`, `ETF_DB_*` 등). Railway 가 런타임 환경변수로 주입하므로
코드 수정 없이 동일하게 동작하며, `.env` 파일은 필요 없습니다.
Dockerfile 이 `PORT` 환경변수를 지원하므로 Railway 의 포트 할당도 자동 적용됩니다.

### 키가 유출된 경우

1. **즉시 해당 키를 폐기(revoke)하고 새 키 발급** — Gemini: Google AI Studio → API Keys.
   git 히스토리에서 지워도 이미 노출된 키는 유효하므로 폐기가 유일한 해결책입니다.
2. 새 키는 `.env`(로컬) / Railway Variables 에만 넣습니다.
3. GitHub 저장소 Settings → Code security 에서 **Secret scanning / Push protection** 을 켜면
   키가 포함된 커밋의 push 자체가 차단됩니다.
