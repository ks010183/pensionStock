import { useState } from 'react'

const KRW = n => Number(n).toLocaleString('ko-KR')

export default function InputScreen({ etfs, onSubmit }) {
  const [accountType, setAccountType] = useState('pension')
  const [cash, setCash] = useState('7000000')
  const [desired, setDesired] = useState('삼성전자 20%, 현대차 10%, 한화 20%')
  const [holdings, setHoldings] = useState([{ etf_code: '069500', amount: 3000000 }])
  const [selEtf, setSelEtf] = useState('')
  const [selAmt, setSelAmt] = useState('')

  const etfName = code => etfs.find(e => e.etf_code === code)?.etf_name || code
  const etfClass = code => etfs.find(e => e.etf_code === code)?.asset_class || ''

  const addHolding = () => {
    if (!selEtf || !selAmt || Number(selAmt) <= 0) return
    setHoldings(h => {
      const other = h.filter(x => x.etf_code !== selEtf)
      return [...other, { etf_code: selEtf, amount: Number(selAmt) }]
    })
    setSelEtf(''); setSelAmt('')
  }

  const canSubmit = desired.trim().length > 0 && Number(cash) >= 0

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
        <h2>희망 포트폴리오 <span className="sub">자유롭게 입력하세요</span></h2>
        <div className="field">
          <textarea
            value={desired}
            onChange={e => setDesired(e.target.value)}
            placeholder="예) 삼성전자 20%, 현대차 10%, 한화 20%"
          />
          <p className="hint">입력분석 Agent가 종목명과 비중을 추출해 DB 종목과 매칭합니다.</p>
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
        <h2>보유 ETF</h2>
        {holdings.length === 0 && <p className="hint">보유 중인 ETF가 없으면 비워 두세요.</p>}
        {holdings.map(h => (
          <div className="holding-item" key={h.etf_code}>
            <div>
              <div className="name">
                {etfName(h.etf_code)}
                <span className={`chip ${etfClass(h.etf_code)}`}>
                  {etfClass(h.etf_code) === 'SAFE' ? '안전' : '위험'}
                </span>
              </div>
              <div className="meta">{h.etf_code}</div>
            </div>
            <div className="row">
              <span className="amt">{KRW(h.amount)}원</span>
              <button className="x-btn" aria-label="삭제"
                onClick={() => setHoldings(hs => hs.filter(x => x.etf_code !== h.etf_code))}>✕</button>
            </div>
          </div>
        ))}
        <div className="row" style={{ marginTop: 10 }}>
          <select className="grow" value={selEtf} onChange={e => setSelEtf(e.target.value)}
            style={{ padding: '10px', borderRadius: 10, border: '1px solid var(--baseline)', background: 'var(--page)', color: 'var(--text-primary)', fontSize: 13 }}>
            <option value="">ETF 선택…</option>
            {etfs.map(e => (
              <option key={e.etf_code} value={e.etf_code}>
                {e.etf_name} ({e.asset_class === 'SAFE' ? '안전' : '위험'})
              </option>
            ))}
          </select>
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <input className="grow" type="number" inputMode="numeric" placeholder="평가금액(원)"
            value={selAmt} onChange={e => setSelAmt(e.target.value)}
            style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid var(--baseline)', background: 'var(--page)', color: 'var(--text-primary)', fontSize: 14 }} />
          <button className="btn small" onClick={addHolding}>추가</button>
        </div>
      </section>

      <button className="btn" disabled={!canSubmit} onClick={() => onSubmit({
        desired_portfolio: desired,
        account: {
          account_type: accountType,
          cash: Number(cash),
          holdings,
        },
      })}>
        최적 ETF 추천받기
      </button>
    </>
  )
}
