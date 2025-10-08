import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

export function SuggestionsTable({ player }: { player: { id: number; name: string } | null }) {
  const [result, setResult] = useState<any>(null)
  const suggest = useMutation({
    mutationFn: async () => {
      if (!player) return null
      const res = await fetch('/api/props/suggest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ playerId: player.id }) })
      return res.json()
    },
    onSuccess: (data) => setResult(data)
  })

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <span>Player:</span>
        <input value={player?.name || ''} disabled style={{ width: 220 }} />
        <button onClick={() => suggest.mutate()} disabled={!player}>Suggest</button>
      </div>
      <div style={{ marginTop: 12 }}>
        {!result ? <div>No suggestions yet.</div> : (
          <pre>{JSON.stringify(result, null, 2)}</pre>
        )}
      </div>
    </div>
  )
}
