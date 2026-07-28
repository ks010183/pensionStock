export default function SimilarScreen({ data }) {
  const results = data.search_results || {}
  const codes = Object.keys(results)
  const comment = data.search_comment

  if (codes.length === 0) {
    return <div className="empty">검색 결과가 없습니다.</div>
  }

  return (
    <>
      {comment && (
        <section className="card">
          <h2>AI 검색 요약 <span className="sub">{comment.provider}</span></h2>
          <p className="ai-comment">{comment.text}</p>
        </section>
      )}
      {codes.map(code => {
        const r = results[code]
        return (
          <section className="card stock-section" key={code}>
            <h2>{r.stock_name} <span className="sub">{code}</span></h2>

            <div className="subhead">이 종목을 포함한 ETF · 구성비율 랭킹 (MCP)</div>
            {(r.etfs || []).length === 0 && <p className="hint">포함 ETF 없음</p>}
            {(r.etfs || []).map(e => (
              <div className="etf-rank" key={e.etf_code}>
                <span>
                  {e.etf_name}
                  <span className={`chip ${e.asset_class}`}>{e.asset_class === 'SAFE' ? '안전' : '위험'}</span>
                </span>
                <span className="w">{Number(e.holding_weight).toFixed(1)}%</span>
              </div>
            ))}

            <div className="subhead">같은 섹터 종목 (MCP)</div>
            <div className="pill-wrap">
              {(r.same_sector || []).length === 0 && <span className="hint">없음</span>}
              {(r.same_sector || []).map(s => (
                <span className="pill" key={s.stock_code}>{s.stock_name} · {s.sector_name}</span>
              ))}
            </div>

            <div className="subhead">같은 테마 종목 (MCP)</div>
            <div className="pill-wrap">
              {(r.same_theme || []).length === 0 && <span className="hint">없음</span>}
              {(r.same_theme || []).map((s, i) => (
                <span className="pill" key={`${s.stock_code}-${i}`}>{s.stock_name} · {s.theme_name}</span>
              ))}
            </div>
          </section>
        )
      })}
    </>
  )
}
