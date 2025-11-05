import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { SuggestionCards } from './SuggestionCards'

export function EnhancedSuggest({ player, filters }: { player: { id: number; name: string } | null, filters: any }) {
  const [result, setResult] = useState<any>(null)
  const suggest = useMutation({
    mutationFn: async () => {
      if (!player || !player.id) return null
      const marketLines = Object.fromEntries(Object.entries(filters.marketLines || {}).filter(([_, v]) => v !== ''))
      const res = await fetch('/api/v1/props/player/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        playerId: player.id,
        season: filters.season || undefined,
        lastN: filters.lastN || undefined,
        home: filters.home === 'any' ? undefined : filters.home,
        marketLines,
      }) })
      return res.json()
    },
    onSuccess: (data) => setResult(data)
  })

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <input value={player?.name || ''} placeholder='Selected player' disabled style={{ width: 280, padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }} />
        <button onClick={() => suggest.mutate()} disabled={!player || !player.id} style={{ padding: '8px 12px' }}>Suggest</button>
      </div>
      <div style={{ marginTop: 12 }}>
        {!result ? <div style={{ color: '#111827' }}>No suggestions yet.</div> : <SuggestionCards suggestions={result.suggestions || []} />}
      </div>
    </div>
  )
}
