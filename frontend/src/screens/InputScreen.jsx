import { useMemo, useState } from 'react'
import SymbolSearch from '../components/SymbolSearch.jsx'

const KRW = n => Number(n).toLocaleString('ko-KR')

// sec_label → 배지 색 클래스
const badgeClass = label =>
  label === '주식' ? 'b-stock' : label === 'ETF' ? 'b-etf' : 'b-etc'

export default function InputScreen({ onSubmit }) {
  const [accountType, setAccountType] = useState('pension')
  const [cash, setCash] = useState('7000000')

  // ---- 희망 포트폴리오 (구조화 입력) ----
  const [entries, setEntries] = useState([])           // [{symbol,name,weight,kind,sec_label,market}]
  const [pendingSym, setPendingSym] = useState(null)   // 자동완성으로 선택된 종목
  const [pendingW, setPendingW] = useState('')
  const [wError, setWError] = useState('')

  const used = useMemo(() => entries.reduce((s, e) => s + e.weight, 0), [entries])
  const remaining = Math.max(0, Math.round((100 - used) * 100) / 100)

  const addEntry = () => {
    const w = Number(pendingW)
    setWError('')
    if (!pendingSym) { setWError('종목을 먼저 검색해 선택하세요.'); return }
    if (!w || w <= 0) { setWError('비율(%)을 입력하세요.'); return }
    if (w > remaining) {
      setWError(`100%를 초과합니다 — 입력 가능한 남은 비율은 ${remaining}% 입니다.`)
      return
    }
    setEntries(list => {
      const other = list.filter(e => e.symbol !== pendingSym.symbol)
      const prev = list.find(e => e.symbol === pendingSym.symbol)
      return [...other, {
        symbol: pendingSym.symbol,
        name: pendingSym.name,
        sec_label: pendingSym.sec_label,
        market: pendingSym.market,
        kind: pendingSym.is_etf_like ? 'etf' : 'stock',
        weight: (prev ? prev.weight : 0) + w,
      }]
    })
    setPendingSym(null)
    setPendingW('')
  }

  // ---- 보유 ETF (자동완성) ----
  const [holdings, setHoldings] = useState([])          // [{etf_code, etf_name, asset_class, amount}]
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
    setPendingEtf(null)
    setPendingAmt('')
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

      <section className="card">
        <h2>희망 포트폴리오
          <span className="sub">주식·ETF 검색 후 비율 입력</span>
        </h2>

        {/* 진행 바 + 잔여 비율 */}
        <div className="alloc-bar">
          <i style={{ width: `${Math.min(100, used)}%` }} />
        </div>
        <p className={`hint ${used > 100 ? 'err' : ''}`} style={{ marginBottom: 10 }}>
          {used > 0 ? `합계 ${used}% 입력됨 · ` : ''}남은 입력 가능 비율 <b>{remaining}%</b>
        </p>

        {/* 추가된 항목 리스트 */}
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
                onClick={() => setEntries(list => list.filter(x => x.symbol !== e.symbol))}>✕</button>
            </div>
          </div>
        ))}

        {/* 종목 검색 + 비율 + 추가 */}
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
      </section>

      <section className="card">
        <h2>매수 가능 현금</h2>
        <div className="field">
          <input
            type="number" inputMode="numeric" min="0" step="100000"
            value={cash} onChange={e => setCash(e.target.value)}
          />
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
                onClick={() => setHoldings(list => list.filter(x => x.etf_code !== h.etf_code))}>✕</button>
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
