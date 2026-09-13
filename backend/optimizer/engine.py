"""ETF 추가매수 최적화 엔진.

문제 정의
---------
고객의 희망 종목 포트폴리오(예: 삼성전자 20%, 현대차 10%, ...)에 대해,
현재 보유 ETF(룩스루 종목 노출)와 매수 가능 현금을 고려하여
"어떤 ETF를 얼마나 추가 매수하면 종목 노출이 목표에 가장 가까워지는가"를 푼다.

수식화 (볼록 이차계획, QP)
--------------------------
- 결정변수 : x_j ≥ 0  (후보 ETF j 의 추가 매수금액, 원)
- 계좌총액 : V = Σ_k h_k + C   (보유 ETF 평가액 + 현금, 매수해도 불변)
- 종목 s 노출금액 : a_s(x) = Σ_k h_k·w_ks + Σ_j x_j·w_js
- 목적함수 : minimize  Σ_s ( a_s(x)/V − t_s )²      (t_s = 목표비중, 비목표 종목은 0)
- 제약조건 :
    (1) Σ_j x_j ≤ C                                  (현금 한도)
    (2) 퇴직연금 계좌:  Σ_{k∈위험} h_k + Σ_{j∈위험} x_j ≤ 0.7·V   (위험자산 70% 규정)
        개인연금 계좌:  제약 없음
    (3) x_j ≥ 0                                       (매수만, 공매도 없음)

목적함수가 x에 대해 볼록 이차식이고 제약이 모두 선형이므로 전역 최적해가 보장된다.
변수 수가 작아(ETF 수십 개) scipy SLSQP 로 빠르고 안정적으로 풀린다.

정수화(1주 단위)는 연속해를 내림(floor) 후 잔여 현금으로 그리디 보정하는
2단계 휴리스틱을 사용한다 — 실무에서 흔한 접근이며 오차가 1주 가격 수준으로 작다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize

RISK_LIMIT_DEFAULT = 0.70


@dataclass
class EtfInfo:
    etf_code: str
    etf_name: str
    asset_class: str            # 'RISK' | 'SAFE'
    close_price: int
    holdings: dict[str, float]  # {stock_code: weight%}


@dataclass
class OptimizationInput:
    target: dict[str, float]          # {stock_code: 목표비중%} (계좌총액 대비)
    owned: dict[str, float]           # {etf_code: 평가금액원}
    cash: float                       # 매수가능 현금(원)
    account_type: str                 # 'pension'(퇴직연금) | 'personal'(개인연금)
    etf_universe: list[EtfInfo]       # 후보 ETF (보유 ETF 포함 전체)
    risk_limit: float = RISK_LIMIT_DEFAULT


@dataclass
class Recommendation:
    etf_code: str
    etf_name: str
    asset_class: str
    amount: float                     # 추천 매수금액(원, 정수화 후)
    shares: int                       # 매수 주수
    price: int
    similarity: float                 # 목표 포트폴리오와의 코사인 유사도


@dataclass
class OptimizationResult:
    recommendations: list[Recommendation]
    before_error: float               # 매수 전 트래킹에러 (RMSE, %p)
    after_error: float                # 매수 후 트래킹에러 (RMSE, %p)
    spent: float                      # 총 매수금액(원)
    remaining_cash: float
    risk_ratio_after: float           # 매수 후 위험자산 비중
    achieved: dict[str, float] = field(default_factory=dict)   # 매수 후 종목별 비중%
    before: dict[str, float] = field(default_factory=dict)     # 매수 전 종목별 비중%
    converged: bool = True
    message: str = ""


def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    keys = set(vec_a) | set(vec_b)
    a = np.array([vec_a.get(k, 0.0) for k in keys])
    b = np.array([vec_b.get(k, 0.0) for k in keys])
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(a @ b / (na * nb))


def optimize(inp: OptimizationInput) -> OptimizationResult:
    universe = inp.etf_universe
    n = len(universe)
    total_value = sum(inp.owned.values()) + inp.cash
    if n == 0 or total_value <= 0:
        return OptimizationResult([], 0, 0, 0, inp.cash, 0, converged=False,
                                  message="후보 ETF 또는 계좌 자산이 없습니다.")

    # ---- 종목 유니버스: 목표 종목 ∪ (보유/후보 ETF 편입 종목) -------------
    stock_ids: list[str] = sorted(
        set(inp.target) | {s for e in universe for s in e.holdings}
    )
    s_idx = {s: i for i, s in enumerate(stock_ids)}
    m = len(stock_ids)

    # 목표비중 벡터 (fraction)
    t = np.zeros(m)
    for s, w in inp.target.items():
        t[s_idx[s]] = w / 100.0

    # ETF 보유비중 행렬 W[m, n] (fraction)
    W = np.zeros((m, n))
    for j, e in enumerate(universe):
        for s, w in e.holdings.items():
            W[s_idx[s], j] = w / 100.0

    # 기존 보유 노출금액 base[m]
    base = np.zeros(m)
    owned_risk_value = 0.0
    e_by_code = {e.etf_code: (j, e) for j, e in enumerate(universe)}
    for code, amt in inp.owned.items():
        if code in e_by_code:
            j, e = e_by_code[code]
            base += W[:, j] * amt
            if e.asset_class == "RISK":
                owned_risk_value += amt

    risk_mask = np.array([1.0 if e.asset_class == "RISK" else 0.0 for e in universe])

    # ---- 목적함수 / 제약 -------------------------------------------------
    V = total_value

    def objective(x: np.ndarray) -> float:
        dev = (base + W @ x) / V - t
        return float(dev @ dev)

    def grad(x: np.ndarray) -> np.ndarray:
        dev = (base + W @ x) / V - t
        return (2.0 / V) * (W.T @ dev)

    constraints = [
        {"type": "ineq", "fun": lambda x: inp.cash - x.sum(),
         "jac": lambda x: -np.ones(n)},
    ]
    if inp.account_type == "pension":
        limit = inp.risk_limit * V - owned_risk_value
        constraints.append(
            {"type": "ineq", "fun": lambda x: limit - risk_mask @ x,
             "jac": lambda x: -risk_mask}
        )

    res = minimize(
        objective, x0=np.zeros(n), jac=grad, method="SLSQP",
        bounds=[(0.0, inp.cash)] * n, constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-12},
    )
    x_cont = np.clip(res.x, 0.0, None)

    # ---- 1주 단위 정수화: 내림 후 그리디 보정 ---------------------------
    prices = np.array([max(e.close_price, 1) for e in universe], dtype=float)
    shares = np.floor(x_cont / prices).astype(int)
    spent = float(shares @ prices)
    leftover = inp.cash - spent
    risk_spent = float((shares * prices) @ risk_mask)
    if inp.account_type == "pension":
        risk_budget = inp.risk_limit * V - owned_risk_value - risk_spent
    else:
        risk_budget = float("inf")

    # 그리디: 한 주 더 샀을 때 목적함수가 가장 많이 줄어드는 ETF부터 추가
    improved = True
    while improved:
        improved = False
        cur = objective(shares * prices)
        best_j, best_val = -1, cur
        for j in range(n):
            p = prices[j]
            if p > leftover:
                continue
            if risk_mask[j] and p > risk_budget:
                continue
            trial = shares * prices
            trial[j] += p
            val = objective(trial)
            if val < best_val - 1e-15:
                best_val, best_j = val, j
        if best_j >= 0:
            shares[best_j] += 1
            leftover -= prices[best_j]
            if risk_mask[best_j]:
                risk_budget -= prices[best_j]
            improved = True

    x_final = shares * prices
    spent = float(x_final.sum())

    # ---- 결과 요약 -------------------------------------------------------
    def rmse(exposure: np.ndarray) -> float:
        dev = exposure / V - t
        return float(np.sqrt(np.mean(dev ** 2)) * 100)

    before_exp = base
    after_exp = base + W @ x_final
    target_vec = {s: t[s_idx[s]] for s in stock_ids}

    recs: list[Recommendation] = []
    for j, e in enumerate(universe):
        if shares[j] > 0:
            sim = cosine_similarity(
                {s: w for s, w in e.holdings.items()},
                {s: v * 100 for s, v in target_vec.items() if v > 0},
            )
            recs.append(Recommendation(
                etf_code=e.etf_code, etf_name=e.etf_name,
                asset_class=e.asset_class,
                amount=float(x_final[j]), shares=int(shares[j]),
                price=e.close_price, similarity=round(sim, 4),
            ))
    recs.sort(key=lambda r: r.amount, reverse=True)

    risk_after = (owned_risk_value + float(x_final @ risk_mask)) / V

    achieved = {s: round(float(after_exp[s_idx[s]] / V * 100), 3)
                for s in stock_ids if after_exp[s_idx[s]] > 0 or t[s_idx[s]] > 0}
    before = {s: round(float(before_exp[s_idx[s]] / V * 100), 3)
              for s in stock_ids if before_exp[s_idx[s]] > 0 or t[s_idx[s]] > 0}

    return OptimizationResult(
        recommendations=recs,
        before_error=round(rmse(before_exp), 4),
        after_error=round(rmse(after_exp), 4),
        spent=spent,
        remaining_cash=round(inp.cash - spent, 2),
        risk_ratio_after=round(risk_after, 4),
        achieved=achieved,
        before=before,
        converged=bool(res.success),
        message="" if res.success else str(res.message),
    )
