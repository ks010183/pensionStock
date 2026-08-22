"""자연어 희망 포트폴리오 분석.

유저의 자유 텍스트에서
  ① 특정 주식/ETF 종목 + 비율 → 구조화 입력 항목으로 자동 변환
  ② 테마 언급 + 비율 → 테마 관련 주식 후보 추천 (유저가 선택해 추가)
을 추출한다.

LLM(입력분석 Agent 에 배정된 프로바이더)이 있으면 LLM 파싱을,
없거나 실패하면 규칙기반(정규식 + 테마 사전 매칭)으로 폴백한다.
"""
from __future__ import annotations

import json
import re
from typing import Any

from backend import database as db
from backend.llm import resolve_for_agent

# 이름(공백 없는 토큰, 조사 허용) + 비율%  — 예: "삼성전자 20%", "현대차를 10%", "반도체에 30%"
_PAIR = re.compile(
    r"([가-힣A-Za-z0-9&\.\-]{2,20}?)(?:을|를|은|는|이|가|에|으로|로)?\s*"
    r"(\d+(?:\.\d+)?)\s*(?:%|퍼센트|프로)"
)

_PARSE_SYSTEM = (
    "당신은 한국 투자자의 자연어 희망 포트폴리오를 구조화하는 분석기입니다. "
    "반드시 JSON 객체만 출력하세요. 다른 텍스트를 붙이지 마세요."
)

_PARSE_PROMPT = """다음 문장에서 투자 희망 내용을 추출하세요.

- 특정 종목(주식/ETF)과 비율 → "stocks" 배열
- 특정 종목이 아닌 산업/테마/섹터 언급(예: AI, 반도체, 방산, 2차전지, 배당)과 비율 → "themes" 배열
- 비율이 명시되지 않았으면 weight 는 null

출력 형식(JSON만):
{"stocks": [{"name": "삼성전자", "weight": 20}],
 "themes": [{"theme": "반도체", "weight": 30}]}

문장: %s"""


def _parse_with_llm_sync_result(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return {"stocks": [], "themes": []}
    data = json.loads(m.group(0))
    return {
        "stocks": data.get("stocks") or [],
        "themes": data.get("themes") or [],
    }


_STOPWORDS = {"각각", "정도", "위주", "비율", "그리고", "나머지", "합계", "전체", "정도로"}


def _parse_with_rules(text: str) -> dict:
    """규칙기반 파싱.

    ① (이름, 비율%) 쌍 추출 → 정확한 종목명이면 종목, 테마 사전 매칭이면 테마
    ② 비율 없이 본문에 언급된 테마도 감지해 후보로 추가 (weight=None)
    """
    theme_dict = db.all_theme_titles()

    def match_theme(phrase: str) -> str | None:
        p = phrase.strip().lower()
        if len(p) < 2:
            return None
        for t in theme_dict:
            title = (t["title"] or "").strip().lower()
            if len(title) >= 2 and (title in p or p in title):
                return t["title"]
            for tag in (t["search_tag"] or "").split("@"):
                tag = tag.strip().lower()
                if len(tag) >= 2 and (tag in p or p in tag):
                    return t["title"]
        return None

    stocks, themes = [], []
    theme_seen: set[str] = set()
    for name, pct in _PAIR.findall(text):
        name = name.strip()
        if name in _STOPWORDS:
            continue
        weight = float(pct)
        hits = db.search_symbols(name, 1)
        nl = name.lower()
        exact = bool(hits) and (
            nl == (hits[0]["name"] or "").lower()
            or nl == (hits[0]["name_en"] or "").lower()
            or nl == hits[0]["symbol"].lower()
        )
        if exact:  # 정확한 종목명/티커 → 종목
            stocks.append({"name": name, "weight": weight})
            continue
        theme = match_theme(name)   # 테마 사전 우선 ("반도체" 등 산업 단어)
        if theme:
            if theme not in theme_seen:
                themes.append({"theme": theme, "weight": weight})
                theme_seen.add(theme)
        elif hits:                  # 근사 종목 매칭
            stocks.append({"name": name, "weight": weight})
        else:
            stocks.append({"name": name, "weight": weight})  # analyze 단계에서 경고 처리

    # ② 비율 없이 언급만 된 테마 감지 (예: "방산이랑 2차전지 위주로")
    low = text.lower()
    for t in theme_dict:
        title = (t["title"] or "").strip()
        if title in theme_seen or len(title) < 2:
            continue
        tokens = [title.lower()] + [
            tag.strip().lower() for tag in (t["search_tag"] or "").split("@")
            if len(tag.strip()) >= 2
        ]
        if any(tok and tok in low for tok in tokens):
            themes.append({"theme": title, "weight": None})
            theme_seen.add(title)

    return {"stocks": stocks, "themes": themes}


async def analyze_text(text: str) -> dict[str, Any]:
    """자연어 → {entries(자동 추가용), theme_suggestions(선택용), warnings, provider}."""
    text = (text or "").strip()
    if not text:
        return {"entries": [], "theme_suggestions": [], "warnings": ["입력이 비어 있습니다."],
                "provider": None}

    warnings: list[str] = []
    provider = None
    llm = resolve_for_agent("INPUT")
    parsed = None
    if llm is not None:
        try:
            raw = await llm.complete(_PARSE_PROMPT % text, system=_PARSE_SYSTEM,
                                     max_tokens=1024)
            parsed = _parse_with_llm_sync_result(raw)
            provider = llm.label
        except Exception as exc:
            warnings.append(f"LLM 분석 실패({exc.__class__.__name__}) → 규칙기반으로 분석했습니다.")
    if parsed is None:
        parsed = _parse_with_rules(text)
        if provider is None and llm is None:
            warnings.append("LLM 미설정 — 규칙기반으로 분석했습니다.")

    # ① 종목 → 심볼 매칭해 자동 추가 항목 생성
    entries: list[dict] = []
    for s in parsed["stocks"]:
        name = str(s.get("name") or "").strip()
        weight = s.get("weight")
        if not name:
            continue
        hits = db.search_symbols(name, 1)
        if not hits:
            # 종목 매칭 실패 → 테마로 재시도
            tc = db.theme_candidates(name)
            if tc and tc["candidates"]:
                parsed["themes"].append({"theme": name, "weight": weight})
            else:
                warnings.append(f"'{name}' 을 종목/테마 어디에서도 찾지 못했습니다.")
            continue
        hit = hits[0]
        entries.append({
            "symbol": hit["symbol"],
            "name": hit["name"],
            "weight": float(weight) if weight else None,
            "kind": "etf" if hit["is_etf_like"] else "stock",
            "sec_label": hit["sec_label"],
            "market": hit["market"],
        })
        if not hit["is_etf_like"] and db.held_etf_count(hit["symbol"]) == 0:
            alts = db.infostock_alternatives(hit["symbol"], hit["name"])
            if alts:
                warnings.append(
                    f"'{hit['name']}' 은 편입한 ETF가 없어 목표 달성이 어렵습니다 — "
                    f"같은 테마 대체 후보: {', '.join(a['name'] for a in alts[:4])}"
                )
            else:
                warnings.append(
                    f"'{hit['name']}' 은 편입한 ETF가 없어 목표 달성이 어렵습니다."
                )

    # ② 테마 → 관련 주식 후보 (달성 가능 종목 우선, 불가 종목은 뒤로/표시)
    theme_suggestions: list[dict] = []
    seen_themes: set[str] = set()
    for t in parsed["themes"]:
        tname = str(t.get("theme") or "").strip()
        if not tname:
            continue
        tc = db.theme_candidates(tname)
        if not tc or not tc["candidates"]:
            warnings.append(f"테마 '{tname}' 의 관련 종목을 찾지 못했습니다.")
            continue
        if tc["theme"] in seen_themes:
            continue
        seen_themes.add(tc["theme"])
        achievable = [c for c in tc["candidates"] if c["held_etf_count"] > 0]
        unachievable = [c for c in tc["candidates"] if c["held_etf_count"] == 0]
        if unachievable:
            warnings.append(
                f"테마 '{tc['theme']}' 중 ETF 로 달성 불가한 종목 제외: "
                + ", ".join(c["name"] for c in unachievable[:5])
                + " — 대신 같은 테마의 다른 종목을 후보로 제시했습니다."
            )
        theme_suggestions.append({
            "theme": tc["theme"],
            "weight": float(t["weight"]) if t.get("weight") else None,
            "candidates": achievable,
            "excluded": [c["name"] for c in unachievable],
        })

    return {
        "entries": entries,
        "theme_suggestions": theme_suggestions,
        "warnings": warnings,
        "provider": provider,
    }
