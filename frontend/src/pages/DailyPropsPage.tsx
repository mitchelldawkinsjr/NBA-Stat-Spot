import { useQuery } from '@tanstack/react-query'
import { SuggestionCards } from '../components/SuggestionCards'

async function fetchDaily(minConfidence?: number) {
  const url = minConfidence ? `/api/v1/props/daily?min_confidence=${minConfidence}` : '/api/v1/props/daily'
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to load')
  return res.json()
}

export default function DailyPropsPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ['daily-props'], queryFn: () => fetchDaily(65) })
  if (isLoading) return <div>Loading…</div>
  if (error) return <div>Error loading props</div>
  const items = (data as any)?.items ?? []
  return (
    <div style={{ padding: 16 }}>
      <h2>Today's Props</h2>
      {items.length === 0 ? <div>No suggestions available.</div> : <SuggestionCards suggestions={items} />}
    </div>
  )
}
