import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <span style={{ display: 'inline-block', background: '#eef2ff', color: '#1f2937', borderRadius: 999, padding: '2px 8px', marginRight: 6, fontSize: 12, border: '1px solid #e5e7eb' }}>{label}: {value}</span>
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
        <input value={player?.name || ''} placeholder="Selected player" disabled style={{ width: 280, padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6, color: '#111827', background: '#fff' }} />
        <button onClick={() => suggest.mutate()} disabled={!player || !player.id} style={{ padding: '8px 12px' }}>Suggest</button>
      </div>
      <div style={{ marginTop: 12 }}>
        {!result ? (
          <div style={{ color: '#374151' }}>No suggestions yet.</div>
        ) : (
          <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden', background: '#ffffff', color: '#111827' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f8fafc', color: '#111827' }}>
                  <th style={{ textAlign: 'left', padding: 10, borderBottom: '1px solid #e5e7eb' }}>Stat</th>
                  <th style={{ textAlign: 'left', padding: 10, borderBottom: '1px solid #e5e7eb' }}>Fair Line</th>
                  <th style={{ textAlign: 'left', padding: 10, borderBottom: '1px solid #e5e7eb' }}>Confidence</th>
                  <th style={{ textAlign: 'left', padding: 10, borderBottom: '1px solid #e5e7eb' }}>Edge</th>
                  <th style={{ textAlign: 'left', padding: 10, borderBottom: '1px solid #e5e7eb' }}>Rationale</th>
                </tr>
              </thead>
              <tbody>
                {result.suggestions.map((s: any, idx: number) => (
                  <tr key={idx} style={{ background: idx % 2 === 0 ? '#ffffff' : '#f9fafb' }}>
                    <td style={{ padding: 10, borderBottom: '1px solid #f3f4f6' }}><strong>{s.type}</strong></td>
                    <td style={{ padding: 10, borderBottom: '1px solid #f3f4f6' }}>{s.fairLine?.toFixed?.(1) ?? '-'}</td>
                    <td style={{ padding: 10, borderBottom: '1px solid #f3f4f6' }}>{s.confidence ? (s.confidence * 100).toFixed(0) + '%' : '-'}</td>
                    <td style={{ padding: 10, borderBottom: '1px solid #f3f4f6' }}>{s.edge != null ? (s.edge * 100).toFixed(1) + '%' : '-'}</td>
                    <td style={{ padding: 10, borderBottom: '1px solid #f3f4f6' }}>
                      {Array.isArray(s.rationale) && s.rationale.length > 0 ? (
                        <div>
                          {s.rationale.map((r: string, i: number) => <StatPill key={i} label={`R${i+1}`} value={r} />)}
                        </div>
                      ) : (
                        <span style={{ color: '#6b7280' }}>—</span>
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
