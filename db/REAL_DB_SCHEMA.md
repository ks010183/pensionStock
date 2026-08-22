# 실제 ETF DB 스키마 정리 (etf_db)

> 로컬 Docker MySQL (`root` / `mysql` / DB: `etf_db`) 기준.
> 덤프 일시 데이터 기준: `dumped_at ≈ 2026-06-12` (db/schema_dump.txt 에서 추출)

## 개요

| 테이블 | 역할 | 행 수 | PK |
|---|---|---:|---|
| `etf_integration` | ETF 기본 정보 (연금매매 가능 여부, 보수, 시세 지표 등 통합) | 1,219 | 없음 (`symbol` 이 사실상 키) |
| `datamart_etfholderkor` | ETF 구성종목 및 비중 | 75,016 | `id` (해시) |
| `datamart_etfsectorweightkor` | ETF 별 섹터 비중 | 8,744 | `id` (해시) |
| `datamart_stockcategorykor` | 테마(카테고리) — 테마별 관련 심볼 매핑 | 1,477 | `id` (해시) |

### 테이블 간 관계 (조인 키)

```
etf_integration.symbol (ETF 티커, 예: '069500')
   ├─ 1:N → datamart_etfholderkor.symbol        (ETF → 구성종목들)
   ├─ 1:N → datamart_etfsectorweightkor.symbol  (ETF → 섹터 비중들)
   └─      datamart_stockcategorykor.symbol / rep_symbol  (테마 → 관련 ETF 심볼)

datamart_etfholderkor.asset (구성종목의 티커, '-1' = 비상장)
```

- 모든 조인 키는 `varchar` 티커(`symbol`)이며 FK 제약은 없다 (애플리케이션 레벨 조인).
- `datamart_*` 3개 테이블은 공통으로 `created_at / updated_at / dumped_at / deleted_at`
  감사 컬럼을 가지며, **`deleted_at IS NULL` 필터가 소프트 삭제 제외 조건**이다.

---

## 1. `etf_integration` — ETF 기본 (50 컬럼)

연금매매 가능 ETF 와 프로젝트에 필요한 ETF 정보를 전처리로 통합한 테이블.
ENGINE=InnoDB, CHARSET=utf8mb4 (COLLATE utf8mb4_0900_ai_ci). 인덱스/PK 없음.

### 식별/기본 정보

| 컬럼 | 타입 | Null | 설명 |
|---|---|---|---|
| `symbol` | varchar(50) | Y | ETF 티커 (예: `069500`) — 사실상 조인 키 |
| `symbol_id` | bigint | N | 내부 심볼 ID |
| `name` / `name_ko` | varchar(500) | Y | 상품명 (영문/한글 — 국내 ETF 는 동일값) |
| `description` | varchar(2500) | Y | 상품 설명 (다수 공백) |
| `domicile` | varchar(500) | Y | 상장 국가 설명문 (예: " is a security listed in the Republic of Korea.") |
| `sec_type` | varchar(500) | Y | 증권 유형 설명문 — **ETF 외에 REIT 등 비-ETF 도 포함됨** (예: 이리츠코크렙) |
| `first_trading_date` | date | Y | 상장일 |
| `status` | varchar(500) | Y | 매매 가능 여부 (예: `active`) |
| `symbol_deleted_at` / `detail_deleted_at` | datetime(6) | Y | 소프트 삭제 시각 |

### 상품 특성

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `bench_mark` | varchar(800) | 추종 지수 (예: `코스피 200`) |
| `leverage_power` | double | 레버리지 배수 (1 = 일반) |
| `origin_etf` | varchar(10) | 원본 ETF 티커 |
| `is_inverse` / `is_leveraged` | varchar(200) | 인버스/레버리지 여부 설명문 (" is not an inverse product" 형태) |
| `product_keyword` | varchar(450) | 상품 키워드 (`@` 구분) |
| `etf_keyword` | varchar(300) | ETF 키워드 (`@` 구분) |
| `pension` | varchar(200) | **연금계좌 매매 가능 구분** (샘플 값: `rp`) |
| `mgmt_strategy` | varchar(200) | 운용 전략 |
| `fund_type` | varchar(20) | 펀드 유형 (예: `주식형`) — **위험/안전자산 분류의 근거 후보** |
| `tax_treatment` | varchar(20) | 과세 구분 (예: `비과세`) |
| `index_replication` | varchar(20) | 지수 복제 방식 (`physical` 등) |

### 보수(비용)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `expense` | double | 총보수(%) |
| `expense_misc` | double | 기타 비용(%) |
| `expense_transaction` | double | 매매·중개 수수료(%) |
| `total_expense` | double | 총비용(%) = 합계 |

### 시세/규모 지표

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `marketcap` | double | 시가총액(원) |
| `nav` | double | 좌당 순자산가치(NAV, 원) |
| `divdend_yield` | double | 배당수익률(%) — 컬럼명 오탈자 주의 (`divdend`) |
| `week52high` / `week52low` | double | 52주 최고/최저가 |
| `week52high_date` / `week52low_date` | varchar(50) | 해당 일자 (`YYYYMMDD` 문자열) |
| `avg_{10,20,40,60,120}_volume` | double | N일 평균 거래량 |
| `avg_{10,20,40,60,120}_amount` | double | N일 평균 거래대금(원) |
| `day_{10,20,40,60,120}_moving_avg` | double | N일 이동평균 종가(원) |
| `last_price` | double | **종가(원) — 매매 주수·비율 계산의 기준가 (2026-08 추가)**. 백엔드는 last_price → day_10_moving_avg → nav 순으로 사용 |
| `dumped_at` | datetime(6) | 적재 시각 |

---

## 2. `datamart_etfholderkor` — ETF 구성종목 (11 컬럼)

ETF 1개 → 구성종목 N행. ENGINE=InnoDB, CHARSET=utf8mb4_unicode_ci.

| 컬럼 | 타입 | Null | 키 | 설명 |
|---|---|---|---|---|
| `id` | varchar(100) | N | PK | 해시 ID |
| `symbol` | varchar(50) | N | IDX | **ETF 티커** (etf_integration.symbol 과 조인) |
| `item_name` | varchar(100) | Y | IDX | 구성종목 이름 (예: `두산밥캣`, `Seagate Technology Holdings PLC`) |
| `weight_percentage` | double | Y | | 구성 비중(%) |
| `shares_number` | double | Y | | 보유 주수 |
| `market_value` | double | Y | | 보유 평가금액(원) |
| `asset` | varchar(100) | Y | IDX | **구성종목 티커**. `-1` = 비상장(현금성/CD 등), 그 외 상장 티커 (해외 티커 포함: `STX`, `CRH` 등) |
| `created_at` | datetime(6) | N | IDX | 생성 시각 |
| `dumped_at` / `deleted_at` / `updated_at` | datetime(6) | Y | IDX | 적재/소프트삭제/수정 시각 |

주의사항
- `symbol` 에는 일반 6자리 티커 외에 `0093D0`, `0162M0` 같은 코드도 존재 (펀드 클래스 코드로 추정).
- 종목 기준 역조회(어떤 ETF 가 삼성전자를 담고 있나)는 `asset`(티커) 또는 `item_name`(이름) 으로 검색.
- 비중 합계는 ETF 별로 100% 미만일 수 있음 (현금/기타 미표시분).

---

## 3. `datamart_etfsectorweightkor` — ETF 섹터 비중 (8 컬럼)

**주식 종목의 섹터가 아니라 ETF 상품 단위의 섹터 구성 비중** 테이블.
ETF 1개 → 섹터 N행. ENGINE=InnoDB, CHARSET=utf8mb4_unicode_ci.

| 컬럼 | 타입 | Null | 키 | 설명 |
|---|---|---|---|---|
| `id` | varchar(100) | N | PK | 해시 ID |
| `symbol` | varchar(50) | N | IDX | **ETF 티커** (etf_integration.symbol 과 조인) |
| `sector_name` | varchar(100) | Y | IDX | 섹터명 (예: `IT`, `원자재`, `현금`, `기타 제조`) |
| `weight_percentage` | double | Y | | 섹터 비중(%) |
| `created_at` | datetime(6) | N | IDX | 생성 시각 |
| `dumped_at` / `deleted_at` / `updated_at` | datetime(6) | Y | IDX | 적재/소프트삭제/수정 시각 |

---

## 4. `datamart_stockcategorykor` — 테마 (10 컬럼)

테마(카테고리)와 관련 심볼의 매핑. 같은 `title`(테마명)이 서로 다른 `symbol` 로
여러 행 존재하는 **테마 → 심볼 N행** 구조. ENGINE=InnoDB, CHARSET=utf8mb4_unicode_ci.

| 컬럼 | 타입 | Null | 키 | 설명 |
|---|---|---|---|---|
| `id` | varchar(100) | N | PK | 해시 ID |
| `title` | varchar(300) | N | IDX | **테마명** (예: `인공지능`, `양자 컴퓨터`, `농산물`, `은`) |
| `description` | varchar(500) | N | IDX | 테마 설명 (문자열 `"null"` 또는 빈 값 다수 — 주의) |
| `rep_symbol` | varchar(10) | Y | IDX | 테마 **대표 심볼**(티커) |
| `search_tag` | varchar(200) | Y | IDX | 검색 키워드 (`@` 구분, 예: `양자컴퓨터@양자컴퓨팅@퀀텀@퀀텀컴퓨팅`) |
| `symbol` | varchar(10) | Y | IDX | 테마에 속한 **개별 심볼**(티커) |
| `created_at` | datetime(6) | N | IDX | 생성 시각 |
| `dumped_at` / `deleted_at` / `updated_at` | datetime(6) | Y | IDX | 적재/소프트삭제/수정 시각 |

---

## 5. `infostock_theme` — 주식-테마 매핑 (2026-08 추가)

주식 종목과 테마 간의 매핑 테이블. **ETF 미편입 종목의 대체 종목 추천**에 사용.

| 컬럼 | 설명 |
|---|---|
| `tmcode` | 테마 코드 |
| `tmname` | 테마명 |
| `tmdetail` | 테마 설명 |
| `itemcd` | 종목 코드 (`A005930` 형태 접두사 가능 — 백엔드에서 정규화) |
| `itemname` | 종목명 |
| `itemdetail` | 종목 설명 |

사용 흐름: 입력 종목의 `held_etf_count`(편입 ETF 수)가 0 이면 →
이 테이블에서 같은 테마(tmcode)의 다른 종목을 공유 테마 수로 랭킹 →
그중 편입 ETF 가 있는(달성 가능한) 종목만 대체 후보로 반환
(`database.infostock_alternatives`, `GET /api/stocks/alternatives`).

---

## 프로젝트(pensionStock) 매핑 가이드

현재 백엔드의 데모 스키마 → 실제 테이블 대응:

| 데모 테이블 | 실제 테이블 | 매핑 메모 |
|---|---|---|
| `etfs` | `etf_integration` | `etf_code→symbol`, `etf_name→name_ko`, `expense_ratio→expense`, `close_price→last_price`(종가, 없으면 day_10_moving_avg→nav 폴백). **asset_class(위험/안전)** 는 `fund_type`/키워드/벤치마크 기반 규칙 필요. **연금 매매 가능**은 `pension` 값과 `status='active'` 로 필터 |
| `etf_holdings` | `datamart_etfholderkor` | `stock_code→asset`(티커) / `stock_name→item_name`, `weight→weight_percentage`. `deleted_at IS NULL` 필터 |
| `sectors`+`stocks.sector_id` | `datamart_etfsectorweightkor` | 실제 DB 는 **종목 섹터가 아닌 ETF 섹터 비중** — "같은 섹터 종목" 도구는 "섹터 비중이 유사한 ETF" 또는 홀딩 교차 기반으로 재정의 필요 |
| `themes`+`stock_themes` | `datamart_stockcategorykor` | `title→테마명`, `symbol/rep_symbol→관련 티커`, `search_tag` 로 키워드 검색 |

공통 주의사항
- 소프트 삭제: `datamart_*` 조회 시 항상 `deleted_at IS NULL`.
- `etf_integration` 에는 REIT 등 비-ETF 포함 → `sec_type LIKE '%exchange-traded fund%'` 필터 권장.
- 인버스/레버리지 제외가 필요하면 `is_inverse`/`is_leveraged`/`leverage_power=1` 활용.
- 수치형 날짜(`week52*_date`)는 `YYYYMMDD` 문자열.
- `pension` 컬럼의 전체 값 분포는 미확인 (샘플에선 `rp`) — 연금 유형별 필터 설계 전에
  `SELECT pension, COUNT(*) FROM etf_integration GROUP BY pension;` 확인 권장.
