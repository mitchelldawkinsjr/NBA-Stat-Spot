import { useQuery } from '@tanstack/react-query'

async function fetchUpcoming() {
  const res = await fetch('/api/schedule/upcoming?hours=24')
  if (!res.ok) throw new Error('Failed to load')
  return res.json()
}

export function GoodBetsDashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ['upcoming'], queryFn: fetchUpcoming })
  if (isLoading) return <div>Loading…</div>
  if (error) return <div>Error loading schedule</div>
  const games = data?.games ?? []
  return (
    <div>
      <h2>Good Bets (Next 24h)</h2>
      {games.length === 0 ? <div>No games available (stub)</div> : (
        <ul>
          {games.map((g: any, idx: number) => (
            <li key={idx}>{JSON.stringify(g)}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
