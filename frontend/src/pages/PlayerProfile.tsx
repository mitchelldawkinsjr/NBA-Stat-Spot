import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useSeason } from '../context/SeasonContext'

type GameLog = {
  game_id: string
  game_date: string
  matchup: string
  pts: number
  reb: number
  ast: number
  tpm: number
}

export default function PlayerProfile() {
  const { id } = useParams()
  const { season } = useSeason()
  const [logs, setLogs] = useState<GameLog[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    (async () => {
      if (!id) return
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`/api/v1/players/${id}/stats?games=20&season=${encodeURIComponent(season)}`)
        if (!res.ok) throw new Error('Failed to load stats')
        const data = await res.json()
        setLogs(data.items || [])
      } catch (e: any) {
        setError(e?.message || 'Error')
      } finally {
        setLoading(false)
      }
    })()
  }, [id, season])

  return (
    <div>
      <h2>Player Profile</h2>
      <div style={{ color: '#6b7280', fontSize: 13, marginTop: 4 }}>Season: {season}</div>
      {loading ? (
        <div style={{ marginTop: 12 }}>Loading…</div>
      ) : error ? (
        <div style={{ marginTop: 12, color: '#b91c1c' }}>Error: {error}</div>
      ) : (
        <div style={{ marginTop: 12, overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>Date</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>Matchup</th>
                <th style={{ textAlign: 'right', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>PTS</th>
                <th style={{ textAlign: 'right', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>REB</th>
                <th style={{ textAlign: 'right', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>AST</th>
                <th style={{ textAlign: 'right', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>3PM</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((g) => (
                <tr key={g.game_id}>
                  <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px' }}>{g.game_date}</td>
                  <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px' }}>{g.matchup}</td>
                  <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px', textAlign: 'right' }}>{g.pts}</td>
                  <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px', textAlign: 'right' }}>{g.reb}</td>
                  <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px', textAlign: 'right' }}>{g.ast}</td>
                  <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px', textAlign: 'right' }}>{g.tpm}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {logs.length === 0 && (
            <div style={{ marginTop: 8, color: '#6b7280' }}>No recent game logs.</div>
          )}
        </div>
      )}
    </div>
  )
}


