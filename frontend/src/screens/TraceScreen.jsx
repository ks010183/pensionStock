export default function TraceScreen({ data }) {
  const trace = data.trace || []
  const acct = data.account_analysis || {}
  const exposure = (acct.exposure_detail || []).slice(0, 12)
  const KRW = n => Number(n).toLocaleString('ko-KR')

  return (
    <>
      <section className="card">
        <h2>멀티 Agent 수행 로그</h2>
        {trace.map((t, i) => (
          <div className="trace-item" key={i}>
            <span className="dot" />
            <div>
              <div className="agent">{t.agent}</div>
              <div className="msg">{t.message}</div>
            </div>
          </div>
        ))}
      </section>

      <section className="card">
        <h2>계좌분석 Agent · 룩스루 종목 노출 <span className="sub">상위 {exposure.length}종목</span></h2>
        {exposure.length === 0 && <p className="hint">보유 ETF가 없어 노출 종목이 없습니다.</p>}
        {exposure.map(e => (
          <div className="etf-rank" key={e.stock_code}>
            <span>{e.stock_name}</span>
            <span className="w">{e.weight.toFixed(2)}%</span>
          </div>
        ))}
        {acct.ai_comment && (
          <p className="ai-comment" style={{ marginTop: 10 }}>
            {acct.ai_comment} <span className="ai-tag">{acct.ai_provider}</span>
          </p>
        )}
        {acct.total_value != null && (
          <p className="hint" style={{ marginTop: 10 }}>
            계좌 총액 {KRW(acct.total_value)}원 = ETF {KRW(acct.etf_value)}원 + 현금 {KRW(acct.cash)}원
            · 위험자산 {((acct.risk_ratio || 0) * 100).toFixed(1)}%
          </p>
        )}
      </section>
    </>
  )
}
