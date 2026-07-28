const KRW = n => Number(n).toLocaleString('ko-KR')

const SERIES = [
  { key: 'target', label: '목표', color: 'var(--series-1)' },
  { key: 'before', label: '매수 전', color: 'var(--series-2)' },
  { key: 'after', label: '매수 후', color: 'var(--series-3)' },
]

const VERDICT = {
  EXECUTABLE: { icon: '✓', title: '실행 가능' },
  CONDITIONAL: { icon: '!', title: '조건부 실행 가능' },
  REJECTED: { icon: '✕', title: '실행 불가' },
}

export default function ResultScreen({ data }) {
  const opt = data.optimization || {}
  const ev = data.evaluation || {}
  const acct = data.account_analysis || {}
  const recs = opt.recommendations || []
  const cmp = (opt.comparison || []).filter(r => r.target > 0)
  const maxVal = Math.max(1, ...cmp.flatMap(r => [r.target, r.before, r.after]))
  const v = VERDICT[ev.verdict] || VERDICT.CONDITIONAL
  const errDelta = (opt.before_error - opt.after_error)

  return (
    <>
      <section className={`card verdict ${ev.verdict}`}>
        <div className="icon">{v.icon}</div>
        <div>
          <div className="title">{v.title}</div>
          <div className="desc">{ev.summary}</div>
        </div>
      </section>

      {ev.ai_comment && (
        <section className="card">
          <h2>AI 종합 의견 <span className="sub">{ev.ai_provider}</span></h2>
          <p className="ai-comment">{ev.ai_comment}</p>
        </section>
      )}

      <div className="tiles">
        <div className="tile">
          <div className="k">트래킹에러 (RMSE)</div>
          <div className="v">{opt.after_error}%p</div>
          <div className={`d ${errDelta > 0 ? 'good' : ''}`}>
            {opt.before_error}%p → {opt.after_error}%p
          </div>
        </div>
        <div className="tile">
          <div className="k">총 매수금액</div>
          <div className="v">{KRW(Math.round(opt.spent || 0))}원</div>
          <div className="d">잔여 현금 {KRW(Math.round(opt.remaining_cash || 0))}원</div>
        </div>
        <div className="tile">
          <div className="k">매수 후 위험자산</div>
          <div className="v">{((opt.risk_ratio_after || 0) * 100).toFixed(1)}%</div>
          <div className="d">
            {acct.account_type === 'pension' ? '한도 70%' : '제한 없음'}
          </div>
        </div>
        <div className="tile">
          <div className="k">추천 ETF</div>
          <div className="v">{recs.length}개</div>
          <div className="d">유사도·QP 최적화 기준</div>
        </div>
      </div>

      <section className="card">
        <h2>추천 매수 ETF <span className="sub">금액 순</span></h2>
        {recs.length === 0 && <p className="hint">추가 매수할 ETF가 없습니다.</p>}
        {opt.ai_comment && (
          <p className="ai-comment" style={{ marginBottom: 10 }}>
            {opt.ai_comment} <span className="ai-tag">{opt.ai_provider}</span>
          </p>
        )}
        {recs.map(r => (
          <div className="rec" key={r.etf_code}>
            <div className="left">
              <div className="name">
                {r.etf_name}
                <span className={`chip ${r.asset_class}`}>{r.asset_class === 'SAFE' ? '안전' : '위험'}</span>
              </div>
              <div className="meta">
                {r.etf_code} · 1주 {KRW(r.price)}원 · 목표 유사도 {(r.similarity * 100).toFixed(0)}%
              </div>
              <div className="simbar"><i style={{ width: `${Math.min(100, r.similarity * 100)}%` }} /></div>
            </div>
            <div className="right">
              <div className="amount">{KRW(Math.round(r.amount))}원</div>
              <div className="shares">{r.shares}주</div>
            </div>
          </div>
        ))}
      </section>

      <section className="card">
        <h2>목표 대비 종목 비중 <span className="sub">계좌 총액 기준 %</span></h2>
        <div className="legend">
          {SERIES.map(s => (
            <div className="item" key={s.key}>
              <span className="swatch" style={{ background: s.color }} />{s.label}
            </div>
          ))}
        </div>
        <div className="cmp-axis">
          {cmp.map(row => (
            <div className="cmp-group" key={row.stock_code}>
              <div className="cmp-label">
                <span>{row.stock_name}</span>
                <span className="val">
                  {row.before.toFixed(1)}% → {row.after.toFixed(1)}% / 목표 {row.target}%
                </span>
              </div>
              <div className="cmp-bars">
                {SERIES.map(s => (
                  <div className="cmp-track" key={s.key}>
                    <div
                      className="cmp-fill"
                      style={{ width: `${(row[s.key] / maxVal) * 100}%`, background: s.color }}
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {(ev.warnings || []).length > 0 && (
        <section className="card">
          <h2>주의사항</h2>
          {ev.warnings.map((w, i) => <div className="warn-item" key={i}>{w}</div>)}
        </section>
      )}

      <section className="card">
        <h2>평가 Agent 체크리스트</h2>
        {(ev.checks || []).map((c, i) => (
          <div className={`check ${c.passed ? 'pass' : 'fail'}`} key={i}>
            <span className="mark">{c.passed ? '✓' : '✕'}</span>
            <div>
              <div className="cname">{c.name}</div>
              <div className="cdetail">{c.detail}</div>
            </div>
          </div>
        ))}
      </section>
    </>
  )
}
