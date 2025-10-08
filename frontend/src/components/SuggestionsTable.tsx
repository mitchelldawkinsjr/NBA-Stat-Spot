import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <span style={{ display: 'inline-block', background: '#f3f4f6', borderRadius: 999, padding: '2px 8px', marginRight: 6, fontSize: 12 }}>{label}: {value}</span>
  )
}

export function SuggestionsTable({ player }: { player: { id: number; name: string } | null }) {
  const [result, setResult] = useState<any>(null)
  const suggest = useMutation({
    mutationFn: async () => {
      if (!player || !player.id) return null
      const res = await fetch('/api/props/suggest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ playerId: player.id, lastN: 10 }) })
      return res.json()
    },
    onSuccess: (data) => setResult(data)
  })

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <input value={player?.name || ''} placeholder="Selected player" disabled style={{ width: 280, padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }} />
        <button onClick={() => suggest.mutate()} disabled={!player || !player.id} style={{ padding: '8px 12px' }}>Suggest</button>
      </div>
      <div style={{ marginTop: 12 }}>
        {!result ? (
          <div style={{ color: '#666' }}>No suggestions yet.</div>
        ) : (
          <div style={{ border: '1px solid #eee', borderRadius: 8, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#fafafa' }}>
                  <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #eee' }}>Stat</th>
                  <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #eee' }}>Fair Line</th>
                  <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #eee' }}>Confidence</th>
                  <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #eee' }}>Edge</th>
                  <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #eee' }}>Rationale</th>
                </tr>
              </thead>
              <tbody>
                {result.suggestions.map((s: any, idx: number) => (
                  <tr key={idx}>
                    <td style={{ padding: 8, borderBottom: '1px solid #f3f4f6' }}><strong>{s.type}</strong></td>
                    <td style={{ padding: 8, borderBottom: '1px solid #f3f4f6' }}>{s.fairLine?.toFixed?.(1) ?? '-'}</td>
                    <td style={{ padding: 8, borderBottom: '1px solid #f3f4f6' }}>{s.confidence ? (s.confidence * 100).toFixed(0) + '%' : '-'}</td>
                    <td style={{ padding: 8, borderBottom: '1px solid #f3f4f6' }}>{s.edge != null ? (s.edge * 100).toFixed(1) + '%' : '-'}</td>
                    <td style={{ padding: 8, borderBottom: '1px solid #f3f4f6' }}>
                      {Array.isArray(s.rationale) && s.rationale.length > 0 ? (
                        <div>
                          {s.rationale.map((r: string, i: number) => <StatPill key={i} label={`R${i+1}`} value={r} />)}
                        </div>
                      ) : (
                        <span style={{ color: '#999' }}>—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
