"""검색 Agent.

MCP(Model Context Protocol) 클라이언트로 ETF DB MCP 서버에 연결하여,
목표 종목에 대해
  - 해당 종목을 포함하는 ETF (구성비율 랭킹)
  - 같은 섹터 / 같은 테마의 유사 종목
을 검색한다. 검색 결과는 최적화 Agent 의 후보 ETF 유니버스 구성과
프론트의 '유사 종목' 표시에 사용된다.

MCP 서버(stdio 서브프로세스) 기동/통신에 실패하는 환경에서는
동일한 SQL 함수를 DB에 직접 호출하는 폴백으로 자동 전환한다
(MCP 도구와 폴백은 backend/database.py 의 같은 함수를 공유하므로 결과 동일).
"""
from __future__ import annotations

import json
from typing import Any

from backend import database as db
from backend.agents.base import BaseAgent
from backend.mcp_client import call_tool, etf_mcp_session


def _root_causes(exc: BaseException) -> str:
    """ExceptionGroup/원인 체인을 풀어 근본 원인 문자열을 만든다."""
    if isinstance(exc, BaseExceptionGroup):
        return "; ".join(_root_causes(e) for e in exc.exceptions)
    if exc.__cause__ is not None and exc.__cause__ is not exc:
        return _root_causes(exc.__cause__)
    return f"{exc.__class__.__name__}: {exc}"


def _to_plain(rows: Any) -> list[dict]:
    """Decimal 등 비-JSON 타입을 문자열/숫자로 정규화 (MCP 응답과 동일 형태)."""
    return json.loads(json.dumps(rows, ensure_ascii=False, default=str))


class SearchAgent(BaseAgent):
    name = "검색Agent"
    llm_key = "SEARCH"

    async def _search_via_mcp(self, target_detail: list[dict]) -> dict[str, dict]:
        results: dict[str, dict] = {}
        async with etf_mcp_session() as session:
            for item in target_detail:
                code, name = item["stock_code"], item["stock_name"]
                etfs = await call_tool(
                    session, "etfs_containing_stock", {"stock": code, "limit": 10}
                )
                sector = await call_tool(
                    session, "stocks_in_same_sector", {"stock": code, "limit": 10}
                )
                theme = await call_tool(
                    session, "stocks_in_same_theme", {"stock": code, "limit": 15}
                )
                results[code] = {
                    "stock_name": name, "etfs": etfs,
                    "same_sector": sector, "same_theme": theme,
                }
        return results

    def _search_via_db(self, target_detail: list[dict]) -> dict[str, dict]:
        """폴백: MCP 도구가 사용하는 것과 동일한 SQL 함수를 직접 호출."""
        results: dict[str, dict] = {}
        for item in target_detail:
            code, name = item["stock_code"], item["stock_name"]
            results[code] = {
                "stock_name": name,
                "etfs": _to_plain(db.etfs_containing_stock(code, 10)),
                "same_sector": _to_plain(db.stocks_in_same_sector(code, 10)),
                "same_theme": _to_plain(db.stocks_in_same_theme(code, 15)),
            }
        return results

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        target_detail: list[dict] = context.get("target_detail", [])

        try:
            results = await self._search_via_mcp(target_detail)
            via = "MCP"
        except Exception as exc:  # MCP 기동/통신 실패 → DB 직접 조회 폴백
            cause = _root_causes(exc)
            self.log(context, f"MCP 연결 실패 → DB 직접 조회 폴백 (원인: {cause})")
            results = self._search_via_db(target_detail)
            via = "DB 폴백"

        candidate_etfs: set[str] = set()
        for r in results.values():
            etfs = r.get("etfs") or []
            if not isinstance(etfs, list):        # 방어: 예상 밖 응답 형태는 무시
                r["etfs"] = etfs = []
            candidate_etfs.update(
                e["etf_code"] for e in etfs if isinstance(e, dict) and "etf_code" in e
            )

        context["search_results"] = results
        context["candidate_etf_codes"] = sorted(candidate_etfs)
        self.log(
            context,
            f"{via} 검색 완료: {len(results)}개 목표종목, 후보 ETF {len(candidate_etfs)}개 발견",
        )

        # 선택적 LLM 코멘트: AGENT_LLM_SEARCH 를 명시했을 때만 호출
        llm = self.get_llm(explicit_only=True)
        if llm is not None and results:
            try:
                lines = []
                for code, r in results.items():
                    themes = {s.get("theme_name") for s in r.get("same_theme", [])}
                    lines.append(
                        f"{r['stock_name']}: 포함 ETF {len(r.get('etfs', []))}개, "
                        f"관련 테마 {', '.join(sorted(t for t in themes if t)) or '없음'}"
                    )
                comment = await llm.complete(
                    prompt=(
                        "다음 검색 결과를 보고 목표 종목별 대체/보완 투자 아이디어를 "
                        "1~2문장으로 요약하세요 (한국어, 사실 기반, 투자권유 아님).\n"
                        + "\n".join(lines)
                    ),
                    max_tokens=1200,
                )
                context["search_comment"] = {"text": comment.strip(), "provider": llm.label}
                self.log(context, f"LLM 검색 요약 생성 ({llm.label})")
            except Exception as exc:
                self.log(context, f"LLM 검색 요약 실패({llm.label}: {exc.__class__.__name__}) → 생략")
        return context
