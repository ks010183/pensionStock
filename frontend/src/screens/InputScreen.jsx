import { useMemo, useState } from 'react'
import SymbolSearch from '../components/SymbolSearch.jsx'

const KRW = n => Number(n).toLocaleString('ko-KR')
const badgeClass = label =>
  label === '주식' ? 'b-stock' : label === 'ETF' ? 'b-etf' : 'b-etc'

export default function InputScreen({ onSubmit }) {
  const [accountType, setAccountType] = useState('pension')
  const [cash, setCash] = useState('7000000')

  // ---- 희망 포트폴리오 (구조화 입력) ----
  const [entries, setEntries] = useState([])
  const [pendingSym, setPendingSym] = useState(null)
  const [pendingW, setPendingW] = useState('')
  const [wError, setWError] = useState('')

  const used = useMemo(() => entries.reduce((s, e) => s + e.weight, 0), [entries])
  const remaining = Math.max(0, Math.round((100 - used) * 100) / 100)

  /** 검증 후 항목 추가 (자동 추가 경로도 공용). 성공 시 실제 추가된 비중을 반환 */
  const pushEntry = (item, weight, { clamp = false } = {}) => {
    const rem = 100 - entries.reduce((s, e) => s + e.weight, 0)
    let w = Number(weight)
    if (!item || !w || w <= 0) return 0
    if (w > rem) {
      if (!clamp || rem <= 0) return -1     // 초과 → 실패
      w = Math.round(rem * 100) / 100       // 자동 추가는 남은 비율로 절삭
    }
    setEntries(list => {
      const other = list.filter(e => e.symbol !== item.symbol)
      const prev = list.find(e => e.symbol === item.symbol)
      return [...other, {
        symbol: item.symbol,
        name: item.name,
        sec_label: item.sec_label || (item.kind === 'etf' ? 'ETF' : '주식'),
        market: item.market || 'KR',
        kind: item.kind || (item.is_etf_like ? 'etf' : 'stock'),
        weight: (prev ? prev.weight : 0) + w,
      }]
    })
    return w
  }

  const addEntry = () => {
    setWError('')
    if (!pendingSym) { setWError('종목을 먼저 검색해 선택하세요.'); return }
    const r = pushEntry(pendingSym, Number(pendingW))
    if (r === 0) { setWError('비율(%)을 입력하세요.'); return }
    if (r === -1) {
      setWError(`100%를 초과합니다 — 입력 가능한 남은 비율은 ${remaining}% 입니다.`)
      return
    }
    setPendingSym(null); setPendingW('')
    setPortfolioSummary(null)
  }

  // ---- 자연어 입력 → LLM/규칙 분석 → 자동 추가 ----
  const [nlText, setNlText] = useState('')
  const [nlBusy, setNlBusy] = useState(false)
  const [nlMsgs, setNlMsgs] = useState([])
  const [themeSugs, setThemeSugs] = useState([])      // [{theme, weight, candidates, selected:Set, wInput}]
  const [pendingNoWeight, setPendingNoWeight] = useState([])  // 비율 미지정 추출 종목

  const analyzeNL = async () => {
    if (!nlText.trim()) return
    setNlBusy(true); setNlMsgs([])
    try {
      const res = await fetch('/api/analyze-input', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: nlText }),
      })
      if (!res.ok) throw new Error(`분석 실패 (${res.status})`)
      const data = await res.json()
      const msgs = [...(data.warnings || [])]

      // 비율이 있는 종목은 자동 추가 (남은 비율 초과분은 절삭)
      let added = 0
      const noWeight = []
      for (const e of data.entries || []) {
        if (e.weight) {
          const w = pushEntry(e, e.weight, { clamp: true })
          if (w > 0) added += 1
          if (w > 0 && w < e.weight) msgs.push(`'${e.name}' 은 남은 비율에 맞춰 ${w}%로 조정해 추가했습니다.`)
          if (w === -1 || w === 0) msgs.push(`'${e.name}' 은 남은 비율이 없어 추가하지 못했습니다.`)
        } else {
          noWeight.push(e)
        }
      }
      if (added > 0) msgs.unshift(`${added}개 종목을 자동으로 추가했습니다.`)
      setPendingNoWeight(noWeight)

      // 테마 제안: 기본 상위 3개 선택 상태로
      setThemeSugs((data.theme_suggestions || []).map(t => ({
        ...t,
        selected: new Set(t.candidates.slice(0, 3).map(c => c.symbol)),
        wInput: t.weight != null ? String(t.weight) : '',
      })))
      if (data.provider) msgs.unshift(`AI 분석 완료 (${data.provider})`)
      setNlMsgs(msgs)
      setPortfolioSummary(null)
    } catch (err) {
      setNlMsgs([String(err.message || err)])
    } finally {
      setNlBusy(false)
    }
  }

  /** 테마 후보 선택 항목들을 비율 분배해 추가 */
  const addThemeSelection = (idx) => {
    const t = themeSugs[idx]
    const sel = t.candidates.filter(c => t.selected.has(c.symbol))
    const W = Number(t.wInput)
    const msgs = []
    if (sel.length === 0) { msgs.push('종목을 1개 이상 선택하세요.'); setNlMsgs(msgs); return }
    if (!W || W <= 0) { msgs.push(`테마 '${t.theme}' 의 비율(%)을 입력하세요.`); setNlMsgs(msgs); return }
    // 선택 종목에 균등 분배 (남은 비율 초과분은 절삭, 나머지는 첫 종목에 보정)
    const per = Math.floor((W / sel.length) * 10) / 10
    let leftover = Math.round((W - per * sel.length) * 10) / 10
    let addedTotal = 0
    for (const c of sel) {
      const w = per + (leftover > 0 ? leftover : 0)
      leftover = 0
      const got = pushEntry(
        { symbol: c.symbol, name: c.name, kind: 'stock', sec_label: '주식', market: 'KR' },
        w, { clamp: true },
      )
      if (got > 0) addedTotal += got
    }
    msgs.push(`테마 '${t.theme}' → ${sel.length}개 종목에 총 ${addedTotal}% 배분 추가했습니다.`)
    setNlMsgs(msgs)
    setThemeSugs(list => list.filter((_, i) => i !== idx))
    setPortfolioSummary(null)
  }

  const toggleCand = (tIdx, symbol) => {
    setThemeSugs(list => list.map((t, i) => {
      if (i !== tIdx) return t
      const sel = new Set(t.selected)
      sel.has(symbol) ? sel.delete(symbol) : sel.add(symbol)
      return { ...t, selected: sel }
    }))
  }

  // ---- 분석 요약 (희망 포트폴리오 / 보유 ETF) ----
  const [portfolioSummary, setPortfolioSummary] = useState(null)
  const [holdingsSummary, setHoldingsSummary] = useState(null)
  const [sumBusy, setSumBusy] = useState('')

  const fetchSummary = async (part) => {
    setSumBusy(part)
    try {
      const body = part === 'portfolio'
        ? { entries: entries.map(e => ({ symbol: e.symbol, name: e.name, weight: e.weight, kind: e.kind })) }
        : { holdings: holdings.map(h => ({ etf_code: h.etf_code, amount: h.amount })), account_type: accountType, cash: Number(cash) }
      const res = await fetch('/api/summarize', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (part === 'portfolio') setPortfolioSummary(data.portfolio)
      else setHoldingsSummary(data.holdings)
    } catch { /* 요약 실패는 무시 */ } finally { setSumBusy('') }
  }

  // ---- 보유 ETF ----
  const [holdings, setHoldings] = useState([])
  const [pendingEtf, setPendingEtf] = useState(null)
  const [pendingAmt, setPendingAmt] = useState('')
  const [hError, setHError] = useState('')

  const addHolding = () => {
    const amt = Number(pendingAmt)
    setHError('')
    if (!pendingEtf) { setHError('ETF를 먼저 검색해 선택하세요.'); return }
    if (!amt || amt <= 0) { setHError('평가금액(원)을 입력하세요.'); return }
    setHoldings(list => {
      const other = list.filter(h => h.etf_code !== pendingEtf.etf_code)
      return [...other, { ...pendingEtf, amount: amt }]
    })
    setPendingEtf(null); setPendingAmt('')
    setHoldingsSummary(null)
  }

  const canSubmit = entries.length > 0 && Number(cash) >= 0

  return (
    <>
      <section className="card">
        <h2>계좌 유형</h2>
        <div className="seg">
          <button className={accountType === 'pension' ? 'on' : ''} onClick={() => setAccountType('pension')}>
            퇴직연금 (DC/IRP)
          </button>
          <button className={accountType === 'personal' ? 'on' : ''} onClick={() => setAccountType('personal')}>
            개인연금
          </button>
        </div>
        <p className="hint">
          {accountType === 'pension'
            ? '퇴직연금은 위험자산 ETF를 계좌 총액의 70%까지만 매수할 수 있습니다.'
            : '개인연금은 위험자산 매수 제한이 없습니다.'}
        </p>
      </section>

      {/* ---- 자연어 입력 ---- */}
      <section className="card">
        <h2>말로 입력하기 <span className="sub">AI가 종목·테마를 추출해 자동 추가</span></h2>
        <div className="field" style={{ marginBottom: 8 }}>
          <textarea
            value={nlText} onChange={e => setNlText(e.target.value)}
            placeholder={'예) 삼성전자 20%, 반도체에 30% 투자하고 싶어요\n예) 방산이랑 2차전지 위주로 구성해줘'}
          />
        </div>
        <button className="btn small" onClick={analyzeNL} disabled={nlBusy || !nlText.trim()}>
          {nlBusy ? '분석 중…' : 'AI로 분석해 추가'}
        </button>
        {nlMsgs.length > 0 && (
          <div style={{ marginTop: 10 }}>
            {nlMsgs.map((m, i) => <p className="hint" key={i} style={{ marginTop: 3 }}>· {m}</p>)}
          </div>
        )}

        {/* 비율 미지정 추출 종목 → 클릭해서 비율 입력 */}
        {pendingNoWeight.length > 0 && (
          <>
            <div className="subhead">비율 미지정 추출 종목 — 누르면 아래 입력창에 선택됩니다</div>
            <div className="pill-wrap">
              {pendingNoWeight.map(e => (
                <button key={e.symbol} className="pill pill-btn"
                  onClick={() => { setPendingSym(e); setPendingNoWeight(l => l.filter(x => x.symbol !== e.symbol)) }}>
                  {e.name} <span className={`tbadge ${badgeClass(e.sec_label)}`}>{e.sec_label}</span>
                </button>
              ))}
            </div>
          </>
        )}

        {/* 테마 후보 선택 */}
        {themeSugs.map((t, i) => (
          <div className="theme-box" key={t.theme + i}>
            <div className="theme-head">
              <b>테마 · {t.theme}</b>
              <span className="hint" style={{ margin: 0 }}>
                관련 종목을 선택하면 비율을 나눠 추가합니다
              </span>
            </div>
            <div className="pill-wrap">
              {t.candidates.map(c => (
                <button key={c.symbol}
                  className={`pill pill-btn ${t.selected.has(c.symbol) ? 'on' : ''}`}
                  onClick={() => toggleCand(i, c.symbol)}>
                  {c.name} <span className="ss-sym">편입ETF {c.held_etf_count}</span>
                </button>
              ))}
            </div>
            {t.excluded?.length > 0 && (
              <p className="hint" style={{ marginTop: 6 }}>
                ETF로 달성 불가해 제외: {t.excluded.join(', ')} → 위 대체 종목으로 채우세요
              </p>
            )}
            <div className="row" style={{ marginTop: 8 }}>
              <input className="grow" type="number" inputMode="decimal" min="0"
                placeholder={`테마 비율 % (남은 ${remaining}%)`}
                value={t.wInput}
                onChange={e => setThemeSugs(list => list.map((x, j) => j === i ? { ...x, wInput: e.target.value } : x))}
                style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid var(--baseline)', background: 'var(--page)', color: 'var(--text-primary)', fontSize: 14 }} />
              <button className="btn small" onClick={() => addThemeSelection(i)}>선택 추가</button>
            </div>
          </div>
        ))}
      </section>

      {/* ---- 구조화 입력 (기존 형식 유지) ---- */}
      <section className="card">
        <h2>희망 포트폴리오 <span className="sub">주식·ETF 검색 후 비율 입력</span></h2>

        <div className="alloc-bar"><i style={{ width: `${Math.min(100, used)}%` }} /></div>
        <p className={`hint ${used > 100 ? 'err' : ''}`} style={{ marginBottom: 10 }}>
          {used > 0 ? `합계 ${used}% 입력됨 · ` : ''}남은 입력 가능 비율 <b>{remaining}%</b>
        </p>

        {entries.map(e => (
          <div className="holding-item" key={e.symbol}>
            <div>
              <div className="name">
                {e.name}
                <span className={`tbadge ${badgeClass(e.sec_label)}`}>{e.sec_label}</span>
                {e.market === 'US' && <span className="tbadge b-etc">US</span>}
              </div>
              <div className="meta">{e.symbol}</div>
            </div>
            <div className="row">
              <span className="amt">{e.weight}%</span>
              <button className="x-btn" aria-label="삭제"
                onClick={() => { setEntries(list => list.filter(x => x.symbol !== e.symbol)); setPortfolioSummary(null) }}>✕</button>
            </div>
          </div>
        ))}

        <div style={{ marginTop: entries.length ? 10 : 0 }}>
          {pendingSym ? (
            <div className="picked">
              <span>
                {pendingSym.name}
                <span className={`tbadge ${badgeClass(pendingSym.sec_label)}`}>{pendingSym.sec_label}</span>
                {pendingSym.market === 'US' && <span className="tbadge b-etc">US</span>}
                <span className="meta" style={{ marginLeft: 6 }}>{pendingSym.symbol}</span>
              </span>
              <button className="x-btn" onClick={() => setPendingSym(null)}>✕</button>
            </div>
          ) : (
            <SymbolSearch
              endpoint="/api/symbols/search"
              placeholder="종목명 또는 티커 검색 (예: 삼성, KODEX, aapl)"
              onSelect={setPendingSym}
              renderItem={it => (
                <span className="ss-row">
                  <span className="ss-name">{it.name}</span>
                  <span className={`tbadge ${badgeClass(it.sec_label)}`}>{it.sec_label}</span>
                  {it.market === 'US' && <span className="tbadge b-etc">US</span>}
                  <span className="ss-sym">{it.symbol}</span>
                </span>
              )}
            />
          )}
          <div className="row" style={{ marginTop: 8 }}>
            <input className="grow" type="number" inputMode="decimal" min="0" max={remaining}
              placeholder={`비율 % (최대 ${remaining}%)`}
              value={pendingW} onChange={e => { setPendingW(e.target.value); setWError('') }}
              style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid var(--baseline)', background: 'var(--page)', color: 'var(--text-primary)', fontSize: 14 }} />
            <button className="btn small" onClick={addEntry} disabled={remaining <= 0}>추가</button>
          </div>
          {wError && <p className="hint err">{wError}</p>}
          {remaining <= 0 && <p className="hint err">비중 합계가 100%에 도달했습니다. 항목을 삭제 후 조정하세요.</p>}
        </div>

        {/* 희망 포트폴리오 분석 요약 */}
        {entries.length > 0 && (
          <div style={{ marginTop: 12 }}>
            {portfolioSummary ? (
              <p className="ai-comment">
                {portfolioSummary.summary}
                {portfolioSummary.provider && <span className="ai-tag">{portfolioSummary.provider}</span>}
              </p>
            ) : (
              <button className="btn ghost" onClick={() => fetchSummary('portfolio')} disabled={sumBusy === 'portfolio'}>
                {sumBusy === 'portfolio' ? '요약 생성 중…' : '희망 포트폴리오 분석 요약'}
              </button>
            )}
          </div>
        )}
      </section>

      <section className="card">
        <h2>매수 가능 현금</h2>
        <div className="field">
          <input type="number" inputMode="numeric" min="0" step="100000"
            value={cash} onChange={e => setCash(e.target.value)} />
          <p className="hint">{cash ? `${KRW(cash)}원` : '금액을 입력하세요'}</p>
        </div>
      </section>

      <section className="card">
        <h2>보유 ETF <span className="sub">ETF 검색 후 평가금액 입력</span></h2>
        {holdings.length === 0 && <p className="hint">보유 중인 ETF가 없으면 비워 두세요.</p>}
        {holdings.map(h => (
          <div className="holding-item" key={h.etf_code}>
            <div>
              <div className="name">
                {h.etf_name}
                <span className={`chip ${h.asset_class}`}>{h.asset_class === 'SAFE' ? '안전' : '위험'}</span>
              </div>
              <div className="meta">{h.etf_code}</div>
            </div>
            <div className="row">
              <span className="amt">{KRW(h.amount)}원</span>
              <button className="x-btn" aria-label="삭제"
                onClick={() => { setHoldings(list => list.filter(x => x.etf_code !== h.etf_code)); setHoldingsSummary(null) }}>✕</button>
            </div>
          </div>
        ))}

        <div style={{ marginTop: holdings.length ? 10 : 0 }}>
          {pendingEtf ? (
            <div className="picked">
              <span>
                {pendingEtf.etf_name}
                <span className={`chip ${pendingEtf.asset_class}`}>{pendingEtf.asset_class === 'SAFE' ? '안전' : '위험'}</span>
                <span className="meta" style={{ marginLeft: 6 }}>{pendingEtf.etf_code}</span>
              </span>
              <button className="x-btn" onClick={() => setPendingEtf(null)}>✕</button>
            </div>
          ) : (
            <SymbolSearch
              endpoint="/api/etfs/search"
              placeholder="보유 ETF 검색 (예: KODEX, 단기채권)"
              onSelect={setPendingEtf}
              renderItem={it => (
                <span className="ss-row">
                  <span className="ss-name">{it.etf_name}</span>
                  <span className={`chip ${it.asset_class}`}>{it.asset_class === 'SAFE' ? '안전' : '위험'}</span>
                  <span className="ss-sym">{it.etf_code}</span>
                </span>
              )}
            />
          )}
          <div className="row" style={{ marginTop: 8 }}>
            <input className="grow" type="number" inputMode="numeric" placeholder="평가금액(원)"
              value={pendingAmt} onChange={e => { setPendingAmt(e.target.value); setHError('') }}
              style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid var(--baseline)', background: 'var(--page)', color: 'var(--text-primary)', fontSize: 14 }} />
            <button className="btn small" onClick={addHolding}>추가</button>
          </div>
          {hError && <p className="hint err">{hError}</p>}
        </div>

        {/* 보유 ETF 분석 요약 */}
        {holdings.length > 0 && (
          <div style={{ marginTop: 12 }}>
            {holdingsSummary ? (
              <p className="ai-comment">
                {holdingsSummary.summary}
                {holdingsSummary.provider && <span className="ai-tag">{holdingsSummary.provider}</span>}
              </p>
            ) : (
              <button className="btn ghost" onClick={() => fetchSummary('holdings')} disabled={sumBusy === 'holdings'}>
                {sumBusy === 'holdings' ? '요약 생성 중…' : '보유 ETF 분석 요약'}
              </button>
            )}
          </div>
        )}
      </section>

      <button className="btn" disabled={!canSubmit} onClick={() => onSubmit({
        desired_portfolio: entries.map(e => ({
          symbol: e.symbol, name: e.name, weight: e.weight, kind: e.kind,
        })),
        account: {
          account_type: accountType,
          cash: Number(cash),
          holdings: holdings.map(h => ({ etf_code: h.etf_code, amount: h.amount })),
        },
      })}>
        최적 ETF 추천받기
      </button>
    </>
  )
}
