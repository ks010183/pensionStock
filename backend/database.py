"""ETF DB 접근 계층 — 실제 DB 스키마 기준 (SQLAlchemy Core + PyMySQL).

실제 테이블 (상세: db/REAL_DB_SCHEMA.md)
  - etf_integration            : ETF 기본 (연금가능 pension, 보수, 시세 등) — 조인키 symbol
  - datamart_etfholderkor      : ETF 구성종목 (symbol=ETF티커, asset=종목티커, item_name=종목명)
  - datamart_etfsectorweightkor: ETF 단위 섹터 비중
  - datamart_stockcategorykor  : 테마 (title=테마명, symbol=관련 티커)

공통 규칙
  - datamart_* 조회는 항상 deleted_at IS NULL (소프트 삭제 제외)
  - ETF 유니버스: status='active' + ETF 타입 + 연금가능(pension) + 비레버리지/비인버스
  - RISK/SAFE 분류: fund_type/키워드 규칙 (config.SAFE_FUND_TYPES / SAFE_NAME_KEYWORDS)
  - 가격(close_price): day_10_moving_avg → nav 순 근사, 없으면 매수 후보 제외
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, text

try:  # 패키지/스크립트 양쪽 실행 지원
    from backend import config
    from backend.config import DATABASE_URL
except ImportError:  # pragma: no cover
    import config  # type: ignore
    from config import DATABASE_URL  # type: ignore

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)

# 연금 매매가능 ETF 유니버스 공통 WHERE (etf_integration alias: e)
_UNIVERSE_WHERE = """
      e.status = 'active'
  AND e.symbol IS NOT NULL
  AND e.symbol_deleted_at IS NULL
  AND e.sec_type LIKE '%exchange-traded fund%'
  AND COALESCE(e.leverage_power, 1) = 1
  AND (e.is_inverse IS NULL OR e.is_inverse LIKE '%not an inverse%')
  AND (e.is_leveraged IS NULL OR e.is_leveraged LIKE '%not a leveraged%')
""" + ("  AND COALESCE(e.pension, '') <> ''\n" if config.UNIVERSE_REQUIRE_PENSION else "")

_ETF_COLS = """
    e.symbol, COALESCE(NULLIF(e.name_ko, ''), e.name, e.symbol) AS etf_name,
    e.fund_type, e.bench_mark, e.etf_keyword, e.product_keyword,
    e.expense, e.total_expense, e.marketcap, e.nav, e.day_10_moving_avg, e.pension
"""


def _rows(sql: str, **params) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        return [dict(r._mapping) for r in result]


# ---------------------------------------------------------------------------
# 분류/가공 헬퍼
# ---------------------------------------------------------------------------

def classify_asset_class(row: dict) -> str:
    """RISK/SAFE 분류: fund_type 목록 → 이름/벤치마크/키워드 순으로 판정."""
    fund_type = (row.get("fund_type") or "").strip()
    if fund_type in config.SAFE_FUND_TYPES:
        return "SAFE"
    haystack = " ".join(
        str(row.get(k) or "")
        for k in ("etf_name", "bench_mark", "etf_keyword", "product_keyword")
    )
    if any(kw in haystack for kw in config.SAFE_NAME_KEYWORDS):
        return "SAFE"
    return "RISK"


def _close_price(row: dict) -> int | None:
    """기준가 근사: 10일 이동평균가 → NAV 순. 둘 다 없으면 None(매수 불가)."""
    for key in ("day_10_moving_avg", "nav"):
        v = row.get(key)
        if v is not None and float(v) > 0:
            return int(round(float(v)))
    return None


def _to_etf_dict(row: dict) -> dict | None:
    price = _close_price(row)
    if price is None:
        return None
    return {
        "etf_code": row["symbol"],
        "etf_name": row["etf_name"],
        "issuer": None,
        "asset_class": classify_asset_class(row),
        "expense_ratio": float(row["total_expense"] or row["expense"] or 0),
        "close_price": price,
        "aum": float(row["marketcap"] or 0),
    }


# ---------------------------------------------------------------------------
# 심볼 마스터 (datamart_symbolkor / datamart_symbolus) — fuzzy 검색·조회
# ---------------------------------------------------------------------------

def sec_type_label(sec_type: str | None) -> str:
    """sec_type 설명문 → 짧은 구분 라벨 (주식/ETF/ETN/단일종목ETF/REIT/기타)."""
    s = sec_type or ""
    if "single stock" in s:
        return "단일종목ETF"
    if "exchange-traded fund" in s:
        return "ETF"
    if "exchange-traded note" in s:
        return "ETN"
    if "real estate" in s:
        return "REIT"
    if "general stock" in s:
        return "주식"
    return "기타"


def _symbol_row_to_dict(r: dict, market: str) -> dict:
    label = sec_type_label(r.get("sec_type"))
    return {
        "symbol": r["symbol"],
        "name": r.get("name_ko") or r.get("name") or r["symbol"],
        "name_en": r.get("name"),
        "market": market,                       # KR | US
        "sec_label": label,                     # 주식 | ETF | ETN | ...
        "is_etf_like": label in ("ETF", "ETN", "단일종목ETF"),
        "order_rank": int(r.get("order_rank") or 0),
    }


def search_symbols(query: str, limit: int = 10) -> list[dict]:
    """국내+해외 심볼 fuzzy 검색 (자동완성용).

    - 매칭: 티커/한글명/영문명 부분일치 (모든 공백 구분 토큰이 포함되어야 함)
    - 랭킹: 정확일치 > 접두일치 > order_rank(1이 가장 중요, 0은 미지정) > 이름 길이
    """
    q = query.strip()
    if not q:
        return []
    tokens = [t for t in q.split() if t]
    cond = " AND ".join(
        f"(symbol LIKE :t{i} OR name_ko LIKE :sub{i} OR name LIKE :sub{i})"
        for i in range(len(tokens))
    )
    params: dict[str, Any] = {}
    for i, t in enumerate(tokens):
        params[f"t{i}"] = f"{t}%"          # 티커는 접두 매칭
        params[f"sub{i}"] = f"%{t}%"       # 이름은 부분 매칭
    fetch = max(limit * 3, 20)

    out: list[dict] = []
    for table, market in (("datamart_symbolkor", "KR"), ("datamart_symbolus", "US")):
        rows = _rows(
            f"""
            SELECT symbol, name, name_ko, sec_type, order_rank
            FROM {table}
            WHERE deleted_at IS NULL AND status = 'active'
              AND symbol IS NOT NULL AND {cond}
            LIMIT {fetch}
            """,
            **params,
        )
        out.extend(_symbol_row_to_dict(r, market) for r in rows)

    ql = q.lower()

    def score(d: dict) -> tuple:
        name, name_en, sym = (d["name"] or "").lower(), (d["name_en"] or "").lower(), d["symbol"].lower()
        exact = ql in (name, name_en, sym)
        prefix = name.startswith(ql) or name_en.startswith(ql) or sym.startswith(ql)
        rank = d["order_rank"] if d["order_rank"] > 0 else 9999
        return (not exact, not prefix, rank, d["market"] != "KR", len(name))

    out.sort(key=score)
    return out[:limit]


def lookup_symbol(symbol: str) -> dict | None:
    """티커 정확일치 조회 (KR 우선, 다음 US). 없으면 etf_integration 에서 보강."""
    for table, market in (("datamart_symbolkor", "KR"), ("datamart_symbolus", "US")):
        rows = _rows(
            f"""
            SELECT symbol, name, name_ko, sec_type, order_rank
            FROM {table}
            WHERE symbol = :s AND deleted_at IS NULL
            LIMIT 1
            """,
            s=symbol,
        )
        if rows:
            return _symbol_row_to_dict(rows[0], market)
    rows = _rows(
        "SELECT symbol, COALESCE(NULLIF(name_ko,''), name) AS name_ko, name, sec_type "
        "FROM etf_integration WHERE symbol = :s LIMIT 1",
        s=symbol,
    )
    if rows:
        return _symbol_row_to_dict({**rows[0], "order_rank": 0}, "KR")
    return None


def search_etfs(query: str, limit: int = 10) -> list[dict]:
    """연금 매매가능 ETF 유니버스 내 fuzzy 검색 (보유 ETF 자동완성용)."""
    q = query.strip()
    if not q:
        return []
    tokens = [t for t in q.split() if t]
    cond = " AND ".join(
        f"(e.symbol LIKE :t{i} OR e.name_ko LIKE :sub{i} OR e.name LIKE :sub{i})"
        for i in range(len(tokens))
    )
    params: dict[str, Any] = {"lim": max(limit * 3, 20)}
    for i, t in enumerate(tokens):
        params[f"t{i}"] = f"{t}%"
        params[f"sub{i}"] = f"%{t}%"
    rows = _rows(
        f"""
        SELECT {_ETF_COLS}
        FROM etf_integration e
        WHERE {_UNIVERSE_WHERE} AND {cond}
        ORDER BY (e.symbol = :exact) DESC, (e.name_ko LIKE :pfx) DESC, e.marketcap DESC
        LIMIT :lim
        """,
        exact=q, pfx=f"{q}%", **params,
    )
    out = []
    for r in rows:
        d = _to_etf_dict(r)
        if d:
            out.append(d)
    return out[:limit]


def held_etf_count(stock_code: str) -> int:
    """이 종목을 편입한 ETF 수 (0 이면 최적화로 목표 달성 불가)."""
    rows = _rows(
        "SELECT COUNT(DISTINCT symbol) AS c FROM datamart_etfholderkor "
        "WHERE asset = :s AND deleted_at IS NULL",
        s=stock_code,
    )
    return int(rows[0]["c"]) if rows else 0


# ---------------------------------------------------------------------------
# 종목 검색
# ---------------------------------------------------------------------------

def find_stock(query: str) -> dict | None:
    """종목명 또는 티커로 주식 1건 조회 (구성종목 테이블 기반).

    실제 DB 에는 별도 주식 마스터가 없어, ETF 구성종목(datamart_etfholderkor)에서
    asset(티커)/item_name(종목명)으로 검색하고 가장 많이 편입된 종목을 선택한다.
    """
    q = query.strip()
    rows = _rows(
        """
        SELECT h.asset AS stock_code,
               MAX(h.item_name) AS stock_name,
               COUNT(DISTINCT h.symbol) AS etf_count,
               MAX(h.item_name = :q) AS exact_name,
               MAX(h.asset = :q) AS exact_code
        FROM datamart_etfholderkor h
        WHERE h.deleted_at IS NULL AND h.asset IS NOT NULL AND h.asset <> '-1'
          AND (h.asset = :q OR h.item_name = :q
               OR h.item_name LIKE CONCAT('%', :q, '%'))
        GROUP BY h.asset
        ORDER BY exact_name DESC, exact_code DESC, etf_count DESC
        LIMIT 1
        """,
        q=q,
    )
    if not rows:
        return None
    stock = rows[0]
    return {
        "stock_code": stock["stock_code"],
        "stock_name": stock["stock_name"],
        "sector_name": dominant_sector_for_stock(stock["stock_code"]),
        "country_code": None,
    }


def dominant_sector_for_stock(stock_code: str) -> str | None:
    """종목의 주력 섹터 추정: 이 종목을 담은 ETF들의 섹터 비중을 편입비중으로 가중합.

    (실제 DB 의 섹터 테이블은 ETF 단위라 종목 섹터를 간접 추정한다)
    """
    rows = _rows(
        """
        SELECT s.sector_name,
               SUM(h.weight_percentage * s.weight_percentage) AS score
        FROM datamart_etfholderkor h
        JOIN datamart_etfsectorweightkor s
          ON s.symbol = h.symbol AND s.deleted_at IS NULL
        WHERE h.asset = :code AND h.deleted_at IS NULL
          AND s.sector_name IS NOT NULL
          AND s.sector_name NOT IN ('현금', '기타')
        GROUP BY s.sector_name
        ORDER BY score DESC
        LIMIT 1
        """,
        code=stock_code,
    )
    return rows[0]["sector_name"] if rows else None


# ---------------------------------------------------------------------------
# MCP 도구용 SQL 함수 3종
# ---------------------------------------------------------------------------

def etfs_containing_stock(stock_query: str, limit: int = 20) -> list[dict]:
    """요청한 주식종목을 포함하는 ETF들을 구성비율 랭킹으로 출력 (연금 유니버스 한정)."""
    stock = find_stock(stock_query)
    if not stock:
        return []
    rows = _rows(
        f"""
        SELECT {_ETF_COLS}, h.weight_percentage AS holding_weight
        FROM datamart_etfholderkor h
        JOIN etf_integration e ON e.symbol = h.symbol
        WHERE h.asset = :code AND h.deleted_at IS NULL
          AND {_UNIVERSE_WHERE}
        ORDER BY h.weight_percentage DESC
        LIMIT :lim
        """,
        code=stock["stock_code"], lim=limit,
    )
    out = []
    for r in rows:
        d = _to_etf_dict(r)
        if d:
            d["holding_weight"] = float(r["holding_weight"] or 0)
            d["stock_name"] = stock["stock_name"]
            out.append(d)
    return out


def stocks_in_same_sector(stock_query: str, limit: int = 20) -> list[dict]:
    """요청한 주식종목과 같은 섹터의 종목들을 출력.

    실제 DB 의 섹터 테이블은 ETF 단위이므로:
    1) 종목의 주력 섹터를 추정(dominant_sector_for_stock)
    2) 그 섹터 비중이 50% 이상인 '섹터 대표 ETF'들의 상위 구성종목을 랭킹으로 반환
    """
    stock = find_stock(stock_query)
    if not stock or not stock.get("sector_name"):
        return []
    sector = stock["sector_name"]
    rows = _rows(
        """
        SELECT h.asset AS stock_code, MAX(h.item_name) AS stock_name,
               :sector AS sector_name, SUM(h.weight_percentage) AS score
        FROM datamart_etfholderkor h
        WHERE h.deleted_at IS NULL AND h.asset IS NOT NULL
          AND h.asset NOT IN ('-1', :code)
          AND h.symbol IN (
              SELECT s.symbol FROM datamart_etfsectorweightkor s
              WHERE s.sector_name = :sector AND s.deleted_at IS NULL
                AND s.weight_percentage >= 50
          )
        GROUP BY h.asset
        ORDER BY score DESC
        LIMIT :lim
        """,
        sector=sector, code=stock["stock_code"], lim=limit,
    )
    return [
        {"stock_code": r["stock_code"], "stock_name": r["stock_name"],
         "sector_name": sector}
        for r in rows
    ]


def stocks_in_same_theme(stock_query: str, limit: int = 30) -> list[dict]:
    """요청한 주식종목과 같은 테마의 심볼들을 출력 (datamart_stockcategorykor).

    테마 매칭: ① 테마 테이블에 종목 티커가 직접 등재된 경우
              ② 테마명/검색태그에 종목명이 포함된 경우
              ③ 종목을 5% 이상 편입한 ETF 가 테마에 등재된 경우 (간접 연결)
    반환 심볼에는 테마 ETF 가 포함될 수 있다 (이름은 etf_integration/구성종목에서 보강).
    """
    stock = find_stock(stock_query)
    if stock:
        code, name = stock["stock_code"], stock["stock_name"]
    else:
        info = lookup_symbol(stock_query)   # ETF 목표 등 구성종목 테이블에 없는 심볼
        if not info:
            return []
        code, name = info["symbol"], info["name"]
    rows = _rows(
        """
        SELECT DISTINCT c2.symbol AS stock_code, c2.title AS theme_name,
               COALESCE(
                   NULLIF(e.name_ko, ''), e.name,
                   (SELECT MAX(h.item_name) FROM datamart_etfholderkor h
                    WHERE h.asset = c2.symbol AND h.deleted_at IS NULL),
                   c2.symbol
               ) AS stock_name
        FROM datamart_stockcategorykor c2
        LEFT JOIN etf_integration e ON e.symbol = c2.symbol
        WHERE c2.deleted_at IS NULL AND c2.symbol IS NOT NULL
          AND c2.symbol <> :code
          AND c2.title IN (
              SELECT DISTINCT c1.title FROM datamart_stockcategorykor c1
              WHERE c1.deleted_at IS NULL
                AND (c1.symbol = :code OR c1.rep_symbol = :code
                     OR c1.title LIKE CONCAT('%', :name, '%')
                     OR c1.search_tag LIKE CONCAT('%', :name, '%')
                     OR c1.symbol IN (
                         SELECT h.symbol FROM datamart_etfholderkor h
                         WHERE h.asset = :code AND h.deleted_at IS NULL
                           AND h.weight_percentage >= 5
                     ))
          )
        ORDER BY c2.title, c2.symbol
        LIMIT :lim
        """,
        code=code, name=name, lim=limit,
    )
    return [
        {"stock_code": r["stock_code"], "stock_name": r["stock_name"],
         "theme_name": r["theme_name"]}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 백엔드(Agent)용 조회 함수
# ---------------------------------------------------------------------------

def all_etfs() -> list[dict]:
    """연금 매매가능 ETF 유니버스 전체 (시총 내림차순, 가격정보 있는 상품만)."""
    rows = _rows(
        f"""
        SELECT {_ETF_COLS}
        FROM etf_integration e
        WHERE {_UNIVERSE_WHERE}
        ORDER BY e.marketcap DESC
        """
    )
    out = []
    for r in rows:
        d = _to_etf_dict(r)
        if d:
            out.append(d)
    return out


def etf_holdings_map(etf_codes: list[str] | None = None) -> dict[str, dict[str, float]]:
    """{etf_code: {stock_code: weight%}} 매핑 (상장 종목만, asset='-1' 제외)."""
    where = "h.deleted_at IS NULL AND h.asset IS NOT NULL AND h.asset <> '-1'"
    if etf_codes:
        codes = ",".join(f"'{c}'" for c in etf_codes)
        where += f" AND h.symbol IN ({codes})"
    rows = _rows(
        f"""
        SELECT h.symbol AS etf_code, h.asset AS stock_code,
               SUM(h.weight_percentage) AS weight
        FROM datamart_etfholderkor h
        WHERE {where}
        GROUP BY h.symbol, h.asset
        """
    )
    out: dict[str, dict[str, float]] = {}
    for r in rows:
        out.setdefault(r["etf_code"], {})[r["stock_code"]] = float(r["weight"] or 0)
    return out


def stock_names(stock_codes: list[str]) -> dict[str, str]:
    """티커 → 이름. 구성종목 → 심볼 마스터(KR/US) → ETF 기본 순으로 보강.

    (목표에 ETF 를 넣은 경우 해당 티커는 구성종목 테이블에 없을 수 있어 폴백 필요)
    """
    if not stock_codes:
        return {}
    uniq = set(stock_codes)
    codes = ",".join(f"'{c}'" for c in uniq)
    out: dict[str, str] = {}
    rows = _rows(
        f"""
        SELECT h.asset AS stock_code, MAX(h.item_name) AS stock_name
        FROM datamart_etfholderkor h
        WHERE h.deleted_at IS NULL AND h.asset IN ({codes})
        GROUP BY h.asset
        """
    )
    out.update({r["stock_code"]: r["stock_name"] for r in rows})
    missing = uniq - set(out)
    if missing:
        mcodes = ",".join(f"'{c}'" for c in missing)
        for table in ("datamart_symbolkor", "datamart_symbolus"):
            rows = _rows(
                f"SELECT symbol, COALESCE(NULLIF(name_ko,''), name) AS n "
                f"FROM {table} WHERE symbol IN ({mcodes}) AND deleted_at IS NULL"
            )
            for r in rows:
                out.setdefault(r["symbol"], r["n"])
        missing = uniq - set(out)
    if missing:
        mcodes = ",".join(f"'{c}'" for c in missing)
        rows = _rows(
            f"SELECT symbol, COALESCE(NULLIF(name_ko,''), name) AS n "
            f"FROM etf_integration WHERE symbol IN ({mcodes})"
        )
        for r in rows:
            out.setdefault(r["symbol"], r["n"])
    return out
