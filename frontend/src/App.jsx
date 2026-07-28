import { useState } from 'react'
import { recommend } from './api.js'
import InputScreen from './screens/InputScreen.jsx'
import ResultScreen from './screens/ResultScreen.jsx'
import SimilarScreen from './screens/SimilarScreen.jsx'
import TraceScreen from './screens/TraceScreen.jsx'

const TABS = [
  { id: 'input', label: '입력', ico: '✎' },
  { id: 'result', label: '추천결과', ico: '◎' },
  { id: 'similar', label: '유사종목', ico: '≈' },
  { id: 'trace', label: 'Agent', ico: '⚙' },
]

export default function App() {
  const [tab, setTab] = useState('input')
  const [accountType, setAccountType] = useState('pension')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (payload) => {
    setLoading(true)
    setError('')
    setAccountType(payload.account.account_type)
    try {
      const data = await recommend(payload)
      setResult(data)
      setTab('result')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="phone">
      <header className="app-header">
        <h1>연금 ETF 최적화</h1>
        <span className={`badge ${accountType === 'pension' ? 'pension' : ''}`}>
          {accountType === 'pension' ? '퇴직연금 · 위험자산 70%' : '개인연금 · 제한없음'}
        </span>
      </header>

      <main className="screen">
        {error && <div className="error-box">{error}</div>}

        {loading && (
          <div className="loading">
            <div className="spinner" />
            멀티 Agent 파이프라인 실행 중…<br />
            입력분석 → 계좌분석 → 검색(MCP) → 최적화 → 평가
          </div>
        )}

        {!loading && tab === 'input' && (
          <InputScreen onSubmit={submit} />
        )}
        {!loading && tab === 'result' && (
          result ? <ResultScreen data={result} /> :
          <div className="empty">먼저 입력 탭에서 희망 포트폴리오와<br />계좌 정보를 입력해 주세요.</div>
        )}
        {!loading && tab === 'similar' && (
          result ? <SimilarScreen data={result} /> :
          <div className="empty">추천 실행 후 MCP 검색 결과가 표시됩니다.</div>
        )}
        {!loading && tab === 'trace' && (
          result ? <TraceScreen data={result} /> :
          <div className="empty">추천 실행 후 Agent 수행 로그가 표시됩니다.</div>
        )}
      </main>

      <nav className="tabbar">
        {TABS.map(t => (
          <button
            key={t.id}
            className={tab === t.id ? 'on' : ''}
            disabled={t.id !== 'input' && !result}
            onClick={() => setTab(t.id)}
          >
            <span className="ico">{t.ico}</span>
            {t.label}
          </button>
        ))}
      </nav>
    </div>
  )
}
