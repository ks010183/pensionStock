const BASE = ''

export async function fetchEtfs() {
  const res = await fetch(`${BASE}/api/etfs`)
  if (!res.ok) throw new Error('ETF 목록을 불러오지 못했습니다.')
  return res.json()
}

export async function recommend(payload) {
  const res = await fetch(`${BASE}/api/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`추천 요청 실패 (${res.status}): ${detail}`)
  }
  return res.json()
}
