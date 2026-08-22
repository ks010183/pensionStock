import { useEffect, useMemo, useRef, useState } from 'react'
import SymbolSearch from '../components/SymbolSearch.jsx'

const KRW = n => Number(n).toLocaleString('ko-KR')
const MIN_CASH = 1_000_000            // 매수 가능 현금 최소값 (원)
const badgeClass = label =>
  label === '주식' ? 'b-stock' : label === 'ETF' ? 'b-etf' : 'b-etc'

const round1 = v => Math.round(v * 10) / 10
const sumW = list => round1(list.reduce((s, e) => s + (Number(e.weight) || 0), 0))

/**
 * 항목 병합 (순수 함수) — 한 이벤트에서 여러 건을 안전하게 추가.
 * source: 'manual'(직접 입력) | 'nl'(AI 분석) | 'theme'(테마 선택)
 * 기존 manual 항목과 병합되면 manual 이 유지되어 AI 재분석 리셋에서 보호된다.
 */
function mergeEntries(base, items, { clamp = false, source = 'manual' } = {}) {
  const msgs = []
  let cur = [...base]
  let added = 0
  for (const it of items) {
    let w = Number(it.weight)
    if (!it.symbol || !w || w <= 0) continue
    const rem = round1(100 - sumW(cur))
    if (w > rem) {
      if (!clamp || rem <= 0) {
        msgs.push(`'${it.name}' 은 남은 비율이 없어 추가하지 못했습니다.`)
        continue
      }
      msgs.push(`'${it.name}' 은 남은 비율에 맞춰 ${rem}%로 조정해 추가했습니다.`)
      w = rem
    }
    const prev = cur.find(e => e.symbol === it.symbol)
    cur = cur.filter(e => e.symbol !== it.symbol)
    cur.push({
      symbol: it.symbol,
      name: it.name,
      sec_label: it.sec_label || (it.kind === 'etf' ? 'ETF' : '주식'),
      market: it.market || 'KR',
      kind: it.kind || (it.is_etf_like ? 'etf' : 'stock'),
      weight: round1((prev ? Number(prev.weight) || 0 : 0) + w),
      source: prev && prev.source === 'manual' ? 'manual' : source,
    })
    added += 1
  }
  return { list: cur, msgs, added }
}

export default function InputScreen({ onSubmit }) {
  const [accountType, setAccountType] = useState('pension')
  const [cash, setCash] = useState(String(MIN_CASH))

  // ---- 희망 포트폴리오 ----
  const [entries, setEntries] = useState([])
  const [pendingSym, setPendingSym] = useState(null)
  const [pendingW, setPendingW] = useState('')
  const [wError, setWError] = useState('')

  const used = useMemo(() => sumW(entries), [entries])
  const remaining = Math.max(0, round1(100 - used))
  const overLimit = used > 100

  const addEntry = () => {
    setWError('')
    if (remaining <= 0) {
      setWError('종목 교체나 비중 조정을 원하실 경우 종목 삭제 후 조정하세요.')
      return
    }
    if (!pendingSym) { setWError('종목을 먼저 검색해 선택하세요.'); return }
    const w = Number(pendingW)
    if (!w || w <= 0) { setWError('비율(%)을 입력하세요.'); return }
    if (w > remaining) {
      setWError(`100%를 초과합니다 — 입력 가능한 남은 비율은 ${remaining}% 입니다.`)
      return
    }
    const r = mergeEntries(entries, [{ ...pendingSym, weight: w }], { source: 'manual' })
    setEntries(r.list)
    setPendingSym(null); setPendingW('')
    setPortfolioSummary(null)
  }

  /** 항목 비율 직접 수정 (AI 분석 결과 포함 모든 항목) */
  const editWeight = (symbol, value) => {
    const w = value === '' ? 0 : Math.max(0, Number(value))
    setEntries(list => list.map(e => e.symbol === symbol ? { ...e, weight: round1(w) } : e))
    setPortfolioSummary(null)
  }

  // ---- 자연어 입력 → 분석 → 자동 추가 (재분석 시 AI 추가분은 리셋) ----
  const [nlText, setNlText] = useState('')
  const [nlBusy, setNlBusy] = useState(false)
  const [nlMsgs, setNlMsgs] = useState([])
  const [themeSugs, setThemeSugs] = useState([])
  const [pendingNoWeight, setPendingNoWeight] = useState([])

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

      // ① 이전 AI 분석 결과(nl/theme 출처)는 리셋하고 직접 입력분만 유지
      const base = entries.filter(e => e.source === 'manual')
      const prevAiCount = entries.length - base.length
      if (prevAiCount > 0) msgs.unshift(`이전 AI 분석 결과 ${prevAiCount}건을 리셋했습니다.`)

      // ② 새 분석 결과 추가 (비율 있는 종목만 자동, 초과분 절삭)
      const withW = (data.entries || []).filter(e => e.weight)
      const noW = (data.entries || []).filter(e => !e.weight)
      const r = mergeEntries(base, withW, { clamp: true, source: 'nl' })
      setEntries(r.list)
      if (r.added > 0) msgs.unshift(`${r.added}개 종목을 자동으로 추가했습니다.`)
      msgs.push(...r.msgs)
      setPendingNoWeight(noW)

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

  const addThemeSelection = (idx) => {
    const t = themeSugs[idx]
    const sel = t.candidates.filter(c => t.selected.has(c.symbol))
    const W = Number(t.wInput)
    if (sel.length === 0) { setNlMsgs(['종목을 1개 이상 선택하세요.']); return }
    if (!W || W <= 0) { setNlMsgs([`테마 '${t.theme}' 의 비율(%)을 입력하세요.`]); return }
    const per = Math.floor((W / sel.length) * 10) / 10
    let leftover = round1(W - per * sel.length)
    const items = sel.map((c, i) => ({
      symbol: c.symbol, name: c.name, kind: 'stock', sec_label: '주식', market: 'KR',
      weight: per + (i === 0 ? leftover : 0),
    }))
    const r = mergeEntries(entries, items, { clamp: true, source: 'theme' })
    setEntries(r.list)
    setNlMsgs([`테마 '${t.theme}' → ${sel.length}개 종목에 배분 추가했습니다.`, ...r.msgs])
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

  // ---- ETF 미편입/편입비중 부족 감지 → 대체·보완 종목 ----
  const [stockInfo, setStockInfo] = useState({})
  const infoFetching = useRef(new Set())

  useEffect(() => {
    for (const e of entries) {
      if (e.kind !== 'stock' || stockInfo[e.symbol] || infoFetching.current.has(e.symbol)) continue
      infoFetching.current.add(e.symbol)
      fetch(`/api/stocks/alternatives?symbol=${encodeURIComponent(e.symbol)}&name=${encodeURIComponent(e.name)}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => {
          if (d) setStockInfo(m => ({
            ...m,
            [e.symbol]: { held: d.held_etf_count, maxW: d.max_etf_weight, alternatives: d.alternatives || [] },
          }))
        })
        .catch(() => {})
        .finally(() => infoFetching.current.delete(e.symbol))
    }
  }, [entries, stockInfo])

  const stockWarnings = useMemo(() => entries
    .filter(e => e.kind === 'stock' && stockInfo[e.symbol])
    .map(e => {
      const info = stockInfo[e.symbol]
      if (info.held === 0) return { type: 'not_held', entry: e, info }
      if (info.maxW > 0 && e.weight > info.maxW) return { type: 'insufficient', entry: e, info }
      return null
    })
    .filter(Boolean), [entries, stockInfo])

  const replaceWithAlternative = (fromSymbol, alt) => {
    setEntries(list => list.map(e => e.symbol === fromSymbol
      ? { ...e, symbol: alt.symbol, name: alt.name, sec_label: '주식', market: 'KR', kind: 'stock' }
      : e))
    setPortfolioSummary(null)
  }

  const splitWithAlternative = (fromSymbol, alt, maxW) => {
    setEntries(list => {
      const from = list.find(e => e.symbol === fromSymbol)
      if (!from) return list
      const keep = Math.floor(Math.min(from.weight, maxW) * 10) / 10
      const rem = round1(from.weight - keep)
      if (rem <= 0) return list
      const others = list.filter(e => e.symbol !== fromSymbol && e.symbol !== alt.symbol)
      const prevAlt = list.find(e => e.symbol === alt.symbol)
      return [
        ...others,
        { ...from, weight: keep },
        {
          symbol: alt.symbol, name: alt.name, sec_label: '주식', market: 'KR',
          kind: 'stock', weight: round1((prevAlt ? prevAlt.weight : 0) + rem),
          source: from.source,
        },
      ]
    })
    setPortfolioSummary(null)
  }

  // ---- 분석 요약 ----
  const [portfolioSummary, setPortfolioSummary] = useState(null)
  const [holdingsSummary, setHoldingsSummary] = useState(null)
  const [sumBusy, setSumBusy] = useState('')

  const fetchSummary = async (part) => {
    setSumBusy(part)
    try {
      const body = part === 'portfolio'
        ? { entries: entries.map(e => ({ symbol: e.symbol, name: e.name, weight: e.weight, kind: e.kind })) }
        : { holdings: holdings.map(h => ({ etf_code: h.etf_code, amount: h.amount })), account_type: accountType, cash: effectiveCash }
      const res = await fetch('/api/summarize', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (part === 'portfolio') setPortfolioSummary(data.portfolio)
      else setHoldingsSummary(data.holdings)
    } catch { /* 요약 실패는 무시 */ } finally { setSumBusy('') }
  }

  // ---- 매수 가능 현금 (최소 100만원) ----
  const cashNum = Number(cash) || 0
  const cashTooLow = cashNum < MIN_CASH
  const effectiveCash = Math.max(MIN_CASH, cashNum)
  const clampCash = () => { if (cashTooLow) setCash(String(MIN_CASH)) }

  // ---- 보유 ETF (보유 주수 입력 → 평가금액 = 주수 × 종가) ----
  const [holdings, setHoldings] = useState([])   // [{etf_code, etf_name, asset_class, close_price, shares, amount}]
  const [pendingEtf, setPendingEtf] = useState(null)
  const [pendingShares, setPendingShares] = useState('')
  const [hError, setHError] = useState('')

  const addHolding = () => {
    const shares = Math.floor(Number(pendingShares))
    setHError('')
    if (!pendingEtf) { setHError('ETF를 먼저 검색해 선택하세요.'); return }
    if (!shares || shares <= 0) { setHError('보유 주수를 입력하세요.'); return }
    const amount = shares * pendingEtf.close_price
    setHoldings(list => {
      const other = list.filter(h => h.etf_code !== pendingEtf.etf_code)
      return [...other, { ...pendingEtf, shares, amount }]
    })
    setPendingEtf(null); setPendingShares('')
    setHoldingsSummary(null)
  }

  // ---- 전체 초기화 ----
  const resetAll = () => {
    setEntries([]); setPendingSym(null); setPendingW(''); setWError('')
    setNlText(''); setNlMsgs([]); setThemeSugs([]); setPendingNoWeight([])
    setHoldings([]); setPendingEtf(null); setPendingShares(''); setHError('')
    setPortfolioSummary(null); setHoldingsSummary(null)
    setCash(String(MIN_CASH)); setAccountType('pension')
    setStockInfo({})
  }

  const canSubmit = entries.length > 0 && !overLimit

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
          <p className="hint">다시 분석하면 이전 AI 분석 결과는 리셋되고 새로 추가됩니다 (직접 입력분은 유지).</p>
        </div>
        <button className="btn small" onClick={analyzeNL} disabled={nlBusy || !nlText.trim()}>
          {nlBusy ? '분석 중…' : 'AI로 분석 후 추가'}
        </button>
        {nlMsgs.length > 0 && (
          <div style={{ marginTop: 10 }}>
            {nlMsgs.map((m, i) => <p className="hint" key={i} style={{ marginTop: 3 }}>· {m}</p>)}
          </div>
        )}

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

      {/* ---- 구조화 입력 ---- */}
      <section className="card">
        <h2>희망 포트폴리오 <span className="sub">비율은 각 항목에서 직접 수정 가능</span></h2>

        <div className="alloc-bar"><i style={{ width: `${Math.min(100, used)}%` }} /></div>
        <p className={`hint ${overLimit ? 'err' : ''}`} style={{ marginBottom: 10 }}>
          {overLimit
            ? `비중 합계가 ${used}%로 100%를 초과했습니다. 아래에서 비율을 조정하세요.`
            : remaining <= 0
              ? '비중 합계가 100% 도달했습니다.'
              : `${used > 0 ? `합계 ${used}% 입력됨 · ` : ''}남은 입력 가능 비율 ` }
          {!overLimit && remaining > 0 && <b>{remaining}%</b>}
        </p>

        {entries.map(e => (
          <div className="holding-item" key={e.symbol}>
            <div>
              <div className="name">
                {e.name}
                <span className={`tbadge ${badgeClass(e.sec_label)}`}>{e.sec_label}</span>
                {e.market === 'US' && <span className="tbadge b-etc">US</span>}
                {e.source !== 'manual' && <span className="tbadge b-etc">AI</span>}
              </div>
              <div className="meta">{e.symbol}</div>
            </div>
            <div className="row">
              <span className="w-edit">
                <input type="number" inputMode="decimal" min="0" step="0.1"
                  value={e.weight}
                  onChange={ev => editWeight(e.symbol, ev.target.value)} />
                %
              </span>
              <button className="x-btn" aria-label="삭제"
                onClick={() => { setEntries(list => list.filter(x => x.symbol !== e.symbol)); setPortfolioSummary(null) }}>✕</button>
            </div>
          </div>
        ))}

        {stockWarnings.map(({ type, entry, info }) => (
          <div className="theme-box alt-box" key={type + entry.symbol}>
            <div className="theme-head">
              {type === 'not_held' ? (
                <>
                  <b>⚠ '{entry.name}' 은 어떤 ETF에도 편입되어 있지 않습니다</b>
                  <span className="hint" style={{ margin: 0 }}>
                    {info.alternatives.length > 0
                      ? '같은 테마의 대체 종목을 누르면 같은 비중으로 교체됩니다'
                      : '대체 종목을 찾지 못했습니다. 이 종목은 최적화에서 달성되지 않습니다.'}
                  </span>
                </>
              ) : (
                <>
                  <b>⚠ '{entry.name}' 목표 {entry.weight}%는 ETF 최대 편입비중({info.maxW}%)을 초과합니다</b>
                  <span className="hint" style={{ margin: 0 }}>
                    {info.alternatives.length > 0
                      ? `보완 종목을 누르면 ${entry.name} ${Math.floor(Math.min(entry.weight, info.maxW) * 10) / 10}% + 보완 종목 ${round1(entry.weight - Math.floor(Math.min(entry.weight, info.maxW) * 10) / 10)}% 로 분할됩니다`
                      : '같은 테마 보완 종목을 찾지 못했습니다. 비중을 낮추는 것을 권장합니다.'}
                  </span>
                </>
              )}
            </div>
            <div className="pill-wrap">
              {info.alternatives.map(a => (
                <button key={a.symbol} className="pill pill-btn"
                  onClick={() => type === 'not_held'
                    ? replaceWithAlternative(entry.symbol, a)
                    : splitWithAlternative(entry.symbol, a, info.maxW)}>
                  {a.name} <span className="ss-sym">{a.themes} · 편입ETF {a.held_etf_count}</span>
                </button>
              ))}
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
              placeholder={remaining > 0 ? `비율 % (최대 ${remaining}%)` : '비율 %'}
              value={pendingW} onChange={e => { setPendingW(e.target.value); setWError('') }}
              style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid var(--baseline)', background: 'var(--page)', color: 'var(--text-primary)', fontSize: 14 }} />
            <button className="btn small" onClick={addEntry}>추가</button>
          </div>
          {wError && <p className="hint err">{wError}</p>}
        </div>

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
        <h2>매수 가능 현금 <span className="sub">최소 {KRW(MIN_CASH)}원</span></h2>
        <div className="field">
          <input type="number" inputMode="numeric" min={MIN_CASH} step="100000"
            value={cash} onChange={e => setCash(e.target.value)} onBlur={clampCash} />
          <p className={`hint ${cashTooLow ? 'err' : ''}`}>
            {cashTooLow
              ? `최소 ${KRW(MIN_CASH)}원 이상이어야 합니다 — ${KRW(MIN_CASH)}원으로 보정됩니다.`
              : `${KRW(cashNum)}원`}
          </p>
        </div>
      </section>

      <section className="card">
        <h2>보유 ETF <span className="sub">ETF 검색 후 보유 주수 입력</span></h2>
        {holdings.length === 0 && <p className="hint">보유 중인 ETF가 없으면 비워 두세요.</p>}
        {holdings.map(h => (
          <div className="holding-item" key={h.etf_code}>
            <div>
              <div className="name">
                {h.etf_name}
                <span className={`chip ${h.asset_class}`}>{h.asset_class === 'SAFE' ? '안전' : '위험'}</span>
              </div>
              <div className="meta">{h.etf_code} · {h.shares}주 × 종가 {KRW(h.close_price)}원</div>
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
                <span className="meta" style={{ marginLeft: 6 }}>종가 {KRW(pendingEtf.close_price)}원</span>
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
            <input className="grow" type="number" inputMode="numeric" min="1" placeholder="보유 주수"
              value={pendingShares} onChange={e => { setPendingShares(e.target.value); setHError('') }}
              style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid var(--baseline)', background: 'var(--page)', color: 'var(--text-primary)', fontSize: 14 }} />
            <button className="btn small" onClick={addHolding}>추가</button>
          </div>
          {pendingEtf && Number(pendingShares) > 0 && (
            <p className="hint">
              평가금액: {KRW(Math.floor(Number(pendingShares)) * pendingEtf.close_price)}원
              ({Math.floor(Number(pendingShares))}주 × {KRW(pendingEtf.close_price)}원)
            </p>
          )}
          {hError && <p className="hint err">{hError}</p>}
        </div>

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

      <div className="row">
        <button className="btn grow" disabled={!canSubmit} onClick={() => onSubmit({
          desired_portfolio: entries.map(e => ({
            symbol: e.symbol, name: e.name, weight: e.weight, kind: e.kind,
          })),
          account: {
            account_type: accountType,
            cash: effectiveCash,
            holdings: holdings.map(h => ({ etf_code: h.etf_code, amount: h.amount })),
          },
        })}>
          최적 ETF 추천받기
        </button>
        <button className="btn ghost" style={{ padding: '14px 16px' }} onClick={resetAll}>
          초기화
        </button>
      </div>
    </>
  )
}
