"""평가 Agent.

입력분석·계좌분석·최적화 Agent 의 결과를 종합하여
추천안의 '매매 실행 가능성'을 평가한다.

평가 항목
  1. 현금 한도 준수 (매수금액 ≤ 매수가능 현금)
  2. 퇴직연금 위험자산 70% 규정 준수
  3. 최적화 수렴 여부
  4. 목표 대비 잔여 괴리 (달성 불가능한 목표 종목 경고)
  5. 개선 효과 (매수 후 트래킹에러가 실제로 감소하는가)

verdict: 'EXECUTABLE' | 'CONDITIONAL' | 'REJECTED'
"""
from __future__ import annotations

from typing import Any

from backend.agents.base import BaseAgent
from backend.config import PENSION_RISK_LIMIT


class EvaluationAgent(BaseAgent):
    name = "평가Agent"
    llm_key = "EVALUATION"

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        opt = context.get("optimization", {})
        acct = context.get("account_analysis", {})
        input_warnings: list[str] = context.get("input_warnings", [])

        checks: list[dict] = []
        warnings: list[str] = list(input_warnings)

        cash = acct.get("cash", 0)
        spent = opt.get("spent", 0)
        checks.append({
            "name": "현금 한도",
            "passed": spent <= cash + 1e-6,
            "detail": f"매수 {spent:,.0f}원 / 가능 {cash:,.0f}원",
        })

        account_type = acct.get("account_type", "pension")
        risk_after = opt.get("risk_ratio_after", 0)
        if account_type == "pension":
            ok = risk_after <= PENSION_RISK_LIMIT + 1e-6
            checks.append({
                "name": "퇴직연금 위험자산 70% 규정",
                "passed": ok,
                "detail": f"매수 후 위험자산 {risk_after*100:.1f}% (한도 {PENSION_RISK_LIMIT*100:.0f}%)",
            })
        else:
            checks.append({
                "name": "개인연금 (위험자산 제한 없음)",
                "passed": True,
                "detail": f"매수 후 위험자산 {risk_after*100:.1f}%",
            })

        checks.append({
            "name": "최적화 수렴",
            "passed": bool(opt.get("converged", False)),
            "detail": opt.get("message") or "정상 수렴",
        })

        before_e, after_e = opt.get("before_error", 0), opt.get("after_error", 0)
        improved = after_e <= before_e + 1e-9
        checks.append({
            "name": "포트폴리오 개선",
            "passed": improved,
            "detail": f"트래킹에러 {before_e}%p → {after_e}%p",
        })

        # 달성 불가 목표 경고 (매수 후에도 목표의 절반에 못 미치는 종목)
        for row in opt.get("comparison", []):
            tgt, aft = row.get("target", 0), row.get("after", 0)
            if tgt > 0 and aft < tgt * 0.5:
                warnings.append(
                    f"'{row['stock_name']}' 목표 {tgt}% 대비 달성 {aft}% — "
                    "해당 종목 비중이 높은 ETF가 부족합니다. 유사 종목/테마 ETF를 참고하세요."
                )

        n_rec = len(opt.get("recommendations", []))
        if n_rec == 0:
            warnings.append("추천할 추가 매수 ETF가 없습니다 (현금 부족 또는 한도 도달).")

        all_passed = all(c["passed"] for c in checks)
        if all_passed and not warnings:
            verdict = "EXECUTABLE"
            summary = "모든 검증을 통과했습니다. 추천안을 그대로 실행할 수 있습니다."
        elif all_passed:
            verdict = "CONDITIONAL"
            summary = "실행은 가능하나 주의사항이 있습니다. 경고 내용을 확인하세요."
        else:
            verdict = "REJECTED"
            summary = "실행 불가 항목이 있습니다. 계좌 조건 또는 목표를 조정하세요."

        # ---- 종합 분석 요약 (항상 생성: 규칙기반 → LLM 있으면 자연문으로 보강) ----
        recs = opt.get("recommendations", [])
        rec_lines = ", ".join(
            f"{r['etf_name']} {r['shares']}주({r['amount']:,.0f}원)" for r in recs
        ) or "없음"
        overall_parts = [summary]
        if recs:
            overall_parts.append(
                f"추천 매수: {rec_lines} — 총 {opt.get('spent', 0):,.0f}원, "
                f"잔여 현금 {opt.get('remaining_cash', 0):,.0f}원."
            )
        overall_parts.append(
            f"목표 대비 비중 괴리(RMSE)는 {before_e}%p 에서 {after_e}%p 로 "
            f"{'개선' if improved else '변화'}되며, 매수 후 위험자산 비중은 "
            f"{risk_after * 100:.1f}% 입니다."
        )
        if warnings:
            overall_parts.append(f"주의사항 {len(warnings)}건을 확인하세요.")
        overall_summary = " ".join(overall_parts)

        evaluation: dict[str, Any] = {
            "verdict": verdict,
            "summary": summary,
            "checks": checks,
            "warnings": warnings,
            "overall_summary": overall_summary,
        }

        # LLM 종합 의견 (이 Agent 에 배정된 프로바이더 사용, 실패해도 평가는 유지)
        llm = self.get_llm()
        if llm is not None:
            try:
                check_lines = "; ".join(
                    f"{c['name']}={'통과' if c['passed'] else '실패'}({c['detail']})"
                    for c in checks
                )
                comment = await llm.complete(
                    prompt=(
                        "다음은 연금계좌 ETF 추가매수 추천안의 검증 결과입니다. "
                        "고객에게 전달할 2~3문장의 종합 의견을 한국어로 작성하세요. "
                        "과장 없이 사실 기반으로, 투자 권유가 아닌 정보 제공 톤으로.\n\n"
                        f"판정: {verdict}\n"
                        f"추천: {rec_lines}\n"
                        f"트래킹에러: {before_e}%p → {after_e}%p\n"
                        f"체크: {check_lines}\n"
                        f"경고: {'; '.join(warnings) or '없음'}"
                    ),
                    system="당신은 연금 포트폴리오 리밸런싱 결과를 고객에게 설명하는 어시스턴트입니다.",
                    max_tokens=1500,
                )
                evaluation["ai_comment"] = comment.strip()
                evaluation["overall_summary"] = comment.strip()   # LLM 요약으로 대체
                evaluation["ai_provider"] = llm.label
                self.log(context, f"LLM 종합의견 생성 ({llm.label})")
            except Exception as exc:
                self.log(context, f"LLM 종합의견 실패({llm.label}: {exc.__class__.__name__}) → 생략")

        context["evaluation"] = evaluation
        self.log(context, f"평가 완료: {verdict} (체크 {len(checks)}건, 경고 {len(warnings)}건)")
        return context
