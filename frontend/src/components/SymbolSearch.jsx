import { useEffect, useRef, useState } from 'react'

/**
 * fuzzy matching 자동완성 검색 입력.
 *
 * props:
 *  - endpoint  : 검색 API 경로 (예: '/api/symbols/search' | '/api/etfs/search')
 *  - onSelect  : (item) => void — 항목 선택 시 호출
 *  - placeholder
 *  - renderItem: (item) => JSX — 드롭다운 행 렌더링 (선택)
 *  - clearOnSelect: 선택 후 입력 비우기 (기본 true)
 */
export default function SymbolSearch({ endpoint, onSelect, placeholder, renderItem, clearOnSelect = true }) {
  const [query, setQuery] = useState('')
  const [items, setItems] = useState([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [hi, setHi] = useState(-1)          // 키보드 하이라이트 인덱스
  const timer = useRef(null)
  const boxRef = useRef(null)

  // 디바운스 검색
  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    const q = query.trim()
    if (q.length < 1) { setItems([]); setOpen(false); return }
    timer.current = setTimeout(async () => {
      setLoading(true)
      try {
        const res = await fetch(`${endpoint}?q=${encodeURIComponent(q)}&limit=8`)
        const data = res.ok ? await res.json() : []
        setItems(data)
        setOpen(true)
        setHi(-1)
      } catch {
        setItems([])
      } finally {
        setLoading(false)
      }
    }, 250)
    return () => timer.current && clearTimeout(timer.current)
  }, [query, endpoint])

  // 바깥 클릭 시 닫기
  useEffect(() => {
    const onDown = e => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [])

  const select = (item) => {
    onSelect(item)
    setOpen(false)
    setItems([])
    setQuery(clearOnSelect ? '' : (item.name || item.etf_name || ''))
  }

  const onKeyDown = e => {
    if (!open || items.length === 0) return
    if (e.key === 'ArrowDown') { e.preventDefault(); setHi(h => Math.min(h + 1, items.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setHi(h => Math.max(h - 1, 0)) }
    else if (e.key === 'Enter' && hi >= 0) { e.preventDefault(); select(items[hi]) }
    else if (e.key === 'Escape') setOpen(false)
  }

  return (
    <div className="ss-box" ref={boxRef}>
      <input
        type="text"
        value={query}
        placeholder={placeholder}
        onChange={e => setQuery(e.target.value)}
        onFocus={() => items.length > 0 && setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {loading && <span className="ss-loading" />}
      {open && (
        <div className="ss-drop">
          {items.length === 0 && <div className="ss-empty">검색 결과 없음</div>}
          {items.map((it, i) => (
            <button
              key={(it.symbol || it.etf_code) + i}
              className={`ss-item ${i === hi ? 'hi' : ''}`}
              onMouseDown={e => { e.preventDefault(); select(it) }}
            >
              {renderItem ? renderItem(it) : (it.name || it.etf_name)}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
