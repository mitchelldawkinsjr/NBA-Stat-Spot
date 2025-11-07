import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { SuggestionCards } from './SuggestionCards'

const TYPES = ['All','PTS','REB','AST','3PM','PRA'] as const
type TypeFilter = typeof TYPES[number]

async function fetchDaily(minConfidence?: number, date?: string) {
  const params = new URLSearchParams()
  if (minConfidence) params.append('min_confidence', minConfidence.toString())
  if (date) params.append('date', date)
  const url = `/api/v1/props/daily${params.toString() ? '?' + params.toString() : ''}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to load')
  return res.json()
}

export function DailyPropsPanel() {
  // Get today's date for filtering - use local date to match what user sees
  const today = new Date().toLocaleDateString('en-CA') // YYYY-MM-DD format in local timezone
  const [minConf, setMinConf] = useState<number>(50)
  const [type, setType] = useState<TypeFilter>('All')
  const [q, setQ] = useState<string>('')
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['daily-props', minConf, today], queryFn: () => fetchDaily(minConf, today) })

  useEffect(() => { refetch() }, [minConf, today])

  const items = (data?.items ?? []) as any[]
  const filtered = useMemo(() => {
    // First filter by date to ensure we only show props for today
    const todayItems = items.filter((item: any) => {
      const itemDate = item.gameDate || item.game_date
      // Must have a date and it must match today
      return itemDate && (itemDate === today || itemDate.startsWith(today))
    })
    // Then apply type and search filters
    return todayItems.filter((s) => (type === 'All' || s.type === type) && (!q || (s.playerName || '').toLowerCase().includes(q.toLowerCase())))
  }, [items, type, q, today])

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff', padding: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ fontWeight: 600 }}>Daily Props</div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <select value={type} onChange={(e) => setType(e.target.value as TypeFilter)} style={{ padding: '6px 8px', border: '1px solid #ddd', borderRadius: 6, background: '#fff' }}>
            {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search player" style={{ padding: '6px 8px', border: '1px solid #ddd', borderRadius: 6 }} />
          <div title="Minimum confidence threshold" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 12, color: '#6b7280' }}>Min Conf</span>
            <input type="range" min={45} max={75} step={1} value={minConf} onChange={(e) => setMinConf(Number(e.target.value))} />
            <span style={{ fontSize: 12 }}>{minConf}%</span>
          </div>
        </div>
      </div>
      <div style={{ marginTop: 10 }}>
        {isLoading ? <div>Loading…</div> : error ? <div>Error loading props</div> : (filtered.length === 0 ? <div>No suggestions available.</div> : <SuggestionCards suggestions={filtered} />)}
      </div>
    </div>
  )
}


