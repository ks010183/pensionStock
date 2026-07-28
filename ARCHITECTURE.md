# 프로젝트 코드 구조 가이드 (ARCHITECTURE.md)

분석·수정을 위한 상세 코드 맵입니다. 전체 흐름 → 디렉터리 구조 → 파일별 상세 →
데이터 계약(입출력 형식) → 수정 시나리오별 가이드 순서로 정리했습니다.

---

## 1. 전체 요청 흐름 (한 번의 추천이 지나가는 경로)

```
[모바일 웹]  frontend (React, :8080)
    │  POST /api/recommend  { desired_portfolio, account }
    ▼
[nginx]  /api/* → backend:8000 프록시            (frontend/nginx.conf)
    ▼
[FastAPI]  main.py :: recommend()                 (요청 검증: pydantic 모델)
    ▼
[오케스트레이터]  agents/orchestrator.py :: run_pipeline()
    │   공유 context(dict) 하나를 5개 Agent 가 순서대로 채워 나감
    │
    ├─① 입력분석Agent  (input_agent.py)
    │     "삼성전자 20%, ..." → LLM/정규식 파싱 → DB 종목 매칭
    │     쓰기: context.target_portfolio / target_detail / input_warnings
    │
    ├─② 계좌분석Agent  (account_agent.py)
    │     보유 ETF 룩스루 → 종목별 노출 합계, 위험자산 비중
    │     쓰기: context.account_analysis / owned / cash / account_type
    │
    ├─③ 검색Agent  (search_agent.py)
    │     MCP 클라이언트 → etf_mcp_server.py (stdio 서브프로세스) → database.py → MySQL
    │     실패 시 database.py 직접 호출로 자동 폴백
    │     쓰기: context.search_results / candidate_etf_codes
    │
    ├─④ 최적화Agent  (optimization_agent.py)
    │     후보 유니버스 구성 → optimizer/engine.py :: optimize() (QP)
    │     쓰기: context.optimization (추천 ETF, 트래킹에러, 비교표)
    │
    └─⑤ 평가Agent  (evaluation_agent.py)
          현금한도/70%규정/수렴/개선 체크 → EXECUTABLE|CONDITIONAL|REJECTED
          쓰기: context.evaluation
    ▼
[FastAPI]  context 를 JSON 응답으로 직렬화 → 프론트 4개 탭이 각 섹션을 렌더링
```

LLM 은 모든 Agent 가 선택적으로 사용: `base.py :: get_llm()` → `llm.py` (anthropic/openai/gemini REST).

---

## 2. 디렉터리 구조

```
pensionStock/
├── docker-compose.yml          # backend + frontend 2개 서비스. 실DB는 host.docker.internal:3306
├── README.md                   # 실행 방법, LLM 설정, 트러블슈팅
├── ARCHITECTURE.md             # (이 문서)
│
├── db/
│   ├── REAL_DB_SCHEMA.md       # ★ 실제 4개 테이블 스키마 상세 (컬럼/조인키/주의사항)
│   ├── schema_dump.txt         # 실DB SHOW CREATE TABLE 원본 덤프
│   ├── dev_seed_real_schema.sql# 실DB 없는 환경용: 동일 DDL + 샘플 데이터 (테스트용)
│   ├── inspect_schema.sh/.sql  # 실DB 스키마 덤프 스크립트
│   ├── inspect_values.sh/.sql  # pension/fund_type 값 분포 덤프 (분류규칙 튜닝용)
│   └── schema.sql, seed.sql    # (구) 데모 스키마 — 참고용, 현재 미사용
│
├── backend/
│   ├── Dockerfile              # python:3.11-slim, uvicorn 기동
│   ├── requirements.txt        # 검증된 버전으로 전부 고정 (mcp==1.27.0 등)
│   ├── config.py               # ★ 모든 설정 (DB/LLM/유니버스/분류규칙) — env 로 오버라이드
│   ├── database.py             # ★ SQL 계층 — 실제 4테이블 조회 전담 (MCP·Agent 공용)
│   ├── llm.py                  # 멀티 프로바이더 LLM 클라이언트 (REST, httpx)
│   ├── mcp_client.py           # MCP stdio 클라이언트 (서버 자동기동 + env 전달)
│   ├── main.py                 # FastAPI 앱: 라우트, CORS, 전역 예외 핸들러
│   │
│   ├── agents/
│   │   ├── base.py             # BaseAgent 추상클래스 (run/log/get_llm)
│   │   ├── orchestrator.py     # PIPELINE 순서 정의 + run_pipeline()
│   │   ├── input_agent.py      # ① 입력분석
│   │   ├── account_agent.py    # ② 계좌분석
│   │   ├── search_agent.py     # ③ 검색 (MCP + DB폴백)
│   │   ├── optimization_agent.py # ④ 최적화
│   │   └── evaluation_agent.py # ⑤ 평가
│   │
│   ├── optimizer/
│   │   └── engine.py           # ★ QP 최적화 엔진 (scipy SLSQP + 그리디 정수화)
│   │
│   └── mcp_server/
│       └── etf_mcp_server.py   # FastMCP stdio 서버 — 도구 3종 노출
│
└── frontend/
    ├── Dockerfile              # node 빌드 → nginx 서빙 (멀티스테이지)
    ├── nginx.conf              # SPA 라우팅 + /api 프록시
    ├── vite.config.js          # 개발서버 :5173, /api → :8000 프록시
    ├── index.html / src/main.jsx
    └── src/
        ├── App.jsx             # 탭 라우팅, 상태(result/loading/error), API 호출
        ├── api.js              # fetch 래퍼 (fetchEtfs / recommend)
        ├── styles.css          # ★ 전체 스타일 (CSS 변수 팔레트, 다크모드, 모바일 프레임)
        └── screens/
            ├── InputScreen.jsx   # 계좌유형/희망포트폴리오/현금/보유ETF 입력
            ├── ResultScreen.jsx  # 판정, 스탯타일, 추천ETF, 목표비교차트, 체크리스트
            ├── SimilarScreen.jsx # MCP 검색결과 (포함ETF 랭킹, 섹터/테마 유사종목)
            └── TraceScreen.jsx   # Agent 수행로그, 룩스루 노출
```

---

## 3. 백엔드 파일별 상세

### config.py — 설정의 단일 진입점
모든 튜닝 포인트가 여기 모여 있고 전부 환경변수로 오버라이드됩니다.

| 그룹 | 항목 | 기본값 |
|---|---|---|
| DB | `ETF_DB_HOST/PORT/USER/PASSWORD/NAME` → `DATABASE_URL` | 127.0.0.1 / etf / etf1234 / etf_db (compose 가 root/mysql 로 덮음) |
| 규정 | `PENSION_RISK_LIMIT` | 0.70 (퇴직연금 위험자산 한도) |
| 유니버스 | `UNIVERSE_REQUIRE_PENSION` | 1 (pension 값 있는 상품만) |
| 분류 | `SAFE_FUND_TYPES`, `SAFE_NAME_KEYWORDS` | 채권형 등 / 채권·국고채·금리 등 |
| 후보 | `MAX_SAFE_CANDIDATES` | 10 (안전자산 후보 시총 상위 N) |
| LLM | `LLM_PROVIDER`(auto), `LLM_MODEL`, `AGENT_LLM_OVERRIDES` | Agent별 `AGENT_LLM_<KEY>` |

### database.py — SQL 계층 (핵심 수정 대상)
실제 4개 테이블에 대한 모든 SQL 이 이 파일에만 존재합니다. Agent/MCP 는 여기의
함수만 호출하므로 **쿼리 수정은 이 파일 하나로 끝납니다**.

| 함수 | 역할 | 핵심 로직 |
|---|---|---|
| `_UNIVERSE_WHERE` (모듈 상수) | 연금 매매가능 ETF 공통 필터 | active + ETF타입 + pension + 비레버리지/인버스 |
| `classify_asset_class(row)` | RISK/SAFE 판정 | fund_type ∈ SAFE_FUND_TYPES → 이름/키워드 매칭 |
| `_close_price(row)` | 기준가 근사 | day_10_moving_avg → nav, 없으면 None(후보 제외) |
| `find_stock(q)` | 종목 검색 | holder 테이블 asset/item_name 매칭, 최다편입 우선 |
| `dominant_sector_for_stock(code)` | 종목 섹터 추정 | 편입 ETF들의 섹터비중 × 편입비중 가중합 |
| `etfs_containing_stock(q, n)` | MCP 도구① | holder JOIN etf_integration, 비중 내림차순 |
| `stocks_in_same_sector(q, n)` | MCP 도구② | 주력섹터 비중≥50% ETF들의 상위 구성종목 |
| `stocks_in_same_theme(q, n)` | MCP 도구③ | 직접등재 ∪ 이름태그 ∪ 5%이상 편입ETF의 테마 |
| `all_etfs()` | 유니버스 전체 | 시총 내림차순, 가격 없는 상품 제외 |
| `etf_holdings_map(codes)` | {ETF: {종목: 비중%}} | deleted_at IS NULL, asset='-1' 제외 |
| `stock_names(codes)` | 티커→이름 | holder 테이블 GROUP BY |

반환 형식은 (구)데모 시절과 동일하게 유지되어 있어 상위 계층은 스키마 교체를 모릅니다:
`all_etfs()` → `{etf_code, etf_name, asset_class, expense_ratio, close_price, aum}`.

### llm.py — 멀티 프로바이더 LLM
- `LLMClient(provider, model).complete(prompt, system, max_tokens)` — async, httpx REST.
  프로바이더별 메서드: `_anthropic()` `_openai()` `_gemini()`. 실패는 `LLMError`.
- `resolve_for_agent(agent_key, explicit_only)` — Agent별 배정 결정:
  `AGENT_LLM_<KEY>` env → 전역 `LLM_PROVIDER`(auto=키 있는 첫 프로바이더) → 키 없으면 None.
- `DEFAULT_MODELS` — 프로바이더별 기본 모델 (여기 수정하면 기본값 변경).

### mcp_client.py — MCP 클라이언트
- `etf_mcp_session()` — etf_mcp_server.py 를 stdio 서브프로세스로 자동 기동.
  **주의: MCP SDK 는 부모 env 를 전달하지 않으므로 `_server_env()` 가
  `ETF_DB_*`/LLM 키를 명시 전달** (이거 빼면 Docker 에서 DB접속 실패 — 과거 버그).
- `call_tool(session, name, args)` — 도구 오류(isError)/비JSON 응답을 예외로 승격
  → 검색Agent 폴백 트리거.

### mcp_server/etf_mcp_server.py — MCP 서버
FastMCP 로 도구 3종(`etfs_containing_stock`, `stocks_in_same_sector`,
`stocks_in_same_theme`)을 노출. 각 도구는 database.py 의 동명 함수를 호출해
JSON 문자열로 반환할 뿐입니다. **도구 추가 시**: 여기에 `@mcp.tool()` 함수 추가
+ database.py 에 SQL 함수 추가.

### agents/ — 멀티 Agent
공통 규약 (base.py):
- `async run(context) -> context` — 입력을 context 에서 읽고 출력을 context 에 기록
- `self.log(context, msg)` — trace 에 수행 로그 축적 (프론트 Agent 탭에 표시)
- `self.get_llm(explicit_only=False)` — 배정된 LLM (없으면 None → 규칙기반)
- `llm_key` — `AGENT_LLM_<llm_key>` env 와 매칭 (INPUT/ACCOUNT/SEARCH/OPTIMIZATION/EVALUATION)

| Agent | 읽는 context | 쓰는 context | LLM 사용 |
|---|---|---|---|
| input_agent | desired_portfolio | target_portfolio {코드:%}, target_detail, input_warnings | 파싱 (전역설정으로도 동작, 실패시 정규식 `_PATTERN`) |
| account_agent | account | account_analysis, owned, cash, account_type | 요약 코멘트 (명시시에만) |
| search_agent | target_detail | search_results, candidate_etf_codes | 요약 코멘트 (명시시에만) |
| optimization_agent | target_portfolio, owned, cash, account_type, candidate_etf_codes | optimization | 배분 설명 (명시시에만) |
| evaluation_agent | optimization, account_analysis, input_warnings | evaluation | 종합의견 (전역설정으로도 동작) |

orchestrator.py 의 `PIPELINE` 리스트가 실행 순서 그 자체입니다.
**Agent 추가**: 새 파일에서 BaseAgent 상속 → PIPELINE 에 삽입하면 끝.

### optimizer/engine.py — QP 최적화 엔진
파일 상단 docstring 에 수식 전체가 있습니다. 요약:
- 변수 `x_j ≥ 0` = ETF j 추가 매수금액. 계좌총액 `V = Σ보유 + 현금` (상수)
- 목적: `min Σ_s ((기존노출_s + Σ x_j·w_js)/V − t_s)²` — 볼록 QP
- 제약: `Σx ≤ 현금`, 퇴직연금이면 `위험보유 + 위험매수 ≤ 0.7V` (선형)
- 풀이: `scipy.optimize.minimize(SLSQP)` + 해석적 gradient (`objective`/`grad`)
- 정수화: 연속해 내림(floor) → 남은 현금으로 "한 주 추가시 목적함수 최대 감소" 그리디
- 입출력 dataclass: `EtfInfo` / `OptimizationInput` / `OptimizationResult(Recommendation[])`
- `cosine_similarity()` — 추천 ETF 의 목표 유사도 표시용 (최적화와는 독립)

**목적함수를 바꾸고 싶으면** `objective()`/`grad()` 만 수정 (둘을 항상 같이 맞출 것).
**제약 추가**는 `constraints` 리스트에 `{"type": "ineq", "fun": ..., "jac": ...}` 추가.

### main.py — API 표면
| 라우트 | 역할 |
|---|---|
| `GET /api/health` | 생존 확인 |
| `GET /api/health/db` | DB 연결 진단 (원인 메시지 포함) |
| `GET /api/etfs` | 유니버스 전체 (보유 ETF 입력 select 용) |
| `GET /api/stocks/search?q=` | 종목 검색 (자동완성용) |
| `POST /api/recommend` | 파이프라인 실행 — 요청: `RecommendIn`, 응답: 아래 4절 |

전역 예외 핸들러 `unhandled_exception_handler` 가 ExceptionGroup 을 재귀 언랩해
근본 원인을 `detail` 로 반환하고, 전체 트레이스백을 uvicorn 로그에 남깁니다.

---

## 4. 데이터 계약 (프론트 ↔ 백엔드)

`POST /api/recommend` 요청:
```json
{
  "desired_portfolio": "삼성전자 20%, 현대차 10%",     // 또는 [{"name":..,"weight":..}]
  "account": {
    "account_type": "pension",                          // pension | personal
    "cash": 7000000,
    "holdings": [{"etf_code": "069500", "amount": 3000000}]
  }
}
```

응답 (context 의 공개 섹션들) — 프론트 탭과 1:1 대응:
```
target_detail      → (Result) 목표 종목 목록 [{stock_code, stock_name, sector_name, weight}]
account_analysis   → (Trace)  {total_value, cash, risk_ratio, owned_detail[], exposure_detail[], ai_comment?}
search_results     → (Similar){종목코드: {stock_name, etfs[], same_sector[], same_theme[]}}
search_comment     → (Similar){text, provider}?          — AGENT_LLM_SEARCH 명시시
optimization       → (Result) {recommendations[{etf_code, etf_name, asset_class, amount,
                               shares, price, similarity}], before_error, after_error,
                               spent, remaining_cash, risk_ratio_after,
                               comparison[{stock_code, stock_name, target, before, after}],
                               converged, ai_comment?}
evaluation         → (Result) {verdict, summary, checks[{name, passed, detail}],
                               warnings[], ai_comment?, ai_provider?}
trace              → (Trace)  [{agent, message}]          — 실행 순서대로
```

---

## 5. 프론트 구조

- **App.jsx**: 단일 상태 컨테이너. `tab`(input/result/similar/trace), `result`(응답 전체),
  `loading`, `error`. 하단 탭바는 result 없으면 비활성. 제출 → `recommend()` → result 저장.
- **screens/**: 각 화면은 props 로 `data`(응답 전체)만 받는 순수 표시 컴포넌트.
  상태 없음 → 응답 JSON 구조만 알면 자유롭게 수정 가능.
- **styles.css**: CSS 변수로 팔레트 정의(`:root` 라이트 / `@media prefers-color-scheme` 다크).
  모바일 프레임은 `.phone { max-width: 430px }`. 차트 색상은 `--series-1/2/3`
  (목표/매수전/매수후 — 접근성 검증된 팔레트이므로 순서 유지 권장).
- **api.js**: BASE 상수가 빈 문자열 → 같은 오리진 `/api` 호출 (개발은 vite 프록시,
  운영은 nginx 프록시가 backend 로 전달).

---

## 6. 수정 시나리오별 가이드

**A. SQL/필터 수정 (예: 유니버스 조건 변경)**
→ `database.py` 의 `_UNIVERSE_WHERE` 또는 해당 함수만. 상위 계층 수정 불필요.
env 로 되는 것(연금필터, SAFE 규칙)은 `config.py`/compose 환경변수 먼저 확인.

**B. MCP 도구 추가 (예: "배당수익률 상위 ETF")**
1. `database.py` 에 SQL 함수 추가
2. `mcp_server/etf_mcp_server.py` 에 `@mcp.tool()` 래퍼 추가
3. 사용처(검색Agent 등)에서 `call_tool(session, "도구명", {...})` 호출
4. 폴백 경로(`search_agent._search_via_db`)에도 동일 함수 추가

**C. Agent 추가 (예: 리스크분석Agent)**
1. `agents/` 에 새 파일, `BaseAgent` 상속, `name`/`llm_key` 지정, `run()` 구현
2. `orchestrator.py` 의 `PIPELINE` 원하는 위치에 삽입
3. 출력을 `context["새키"]` 에 쓰고 `main.py` 응답 dict 에 추가
4. 프론트에서 해당 키 렌더링

**D. 최적화 로직 수정 (예: 거래비용 반영)**
→ `optimizer/engine.py`. 목적함수에 `Σ c_j·x_j` (c=보수율) 추가하려면
`objective`/`grad` 에 선형항 추가. 제약 추가는 `constraints` 리스트.
수정 후 반드시 퇴직연금 70% 경계 시나리오로 검증.

**E. LLM 프로바이더 추가 (예: 로컬 Ollama)**
→ `llm.py`: `DEFAULT_MODELS` 에 항목 추가 + `_api_key()` + `complete()` 분기
+ `_<provider>()` 메서드 구현. Agent 코드는 수정 불필요.

**F. 화면 수정**
→ `screens/*.jsx` (데이터는 4절 계약 참조) + `styles.css`.
새 데이터가 필요하면: Agent 가 context 에 쓰고 → main.py 응답에 추가 → 화면에서 사용.

**G. 프롬프트 수정**
→ 각 Agent 파일 안의 `llm.complete(prompt=..., system=...)` 호출부.
입력분석 파싱 프롬프트: `input_agent.py :: _parse_with_llm` / `_PARSE_SYSTEM`.

---

## 7. 개발·테스트 루프

```bash
# 백엔드만 재빌드/재기동 (코드 수정 후)
docker compose up -d --build backend
docker compose logs -f backend          # 전체 트레이스백 + Agent 로그

# DB 연결 진단
curl http://localhost:8080/api/health/db

# 파이프라인 단독 테스트 (컨테이너 없이)
ETF_DB_HOST=127.0.0.1 ETF_DB_USER=root ETF_DB_PASSWORD=mysql python3 -c "
import asyncio, sys; sys.path.insert(0, '.')
from backend.agents.orchestrator import run_pipeline
ctx = asyncio.run(run_pipeline('삼성전자 20%', {'account_type':'pension','cash':1000000,'holdings':[]}))
print(ctx['evaluation']['verdict'])"

# 프론트 개발 모드 (핫리로드, /api 는 :8000 프록시)
cd frontend && npm run dev              # http://localhost:5173

# 실DB 없는 환경에서 테스트용 테이블 구성
mysql --default-character-set=utf8mb4 -u root < db/dev_seed_real_schema.sql
```

### 함정 목록 (실제로 겪은 것들)
1. SQL 파일 로드 시 `--default-character-set=utf8mb4` 누락 → 한글 깨져 종목 매칭 전멸
2. MySQL 8 인증(caching_sha2) → `cryptography` 패키지 필수 (requirements 에 포함됨)
3. MCP 서브프로세스는 부모 env 를 못 받음 → `mcp_client._server_env()` 가 명시 전달
4. `datamart_*` 조회 시 `deleted_at IS NULL` 누락하면 삭제행이 섞임
5. requirements 버전 고정 해제 시 컨테이너-로컬 동작 차이 발생 가능 (mcp 등)
```
