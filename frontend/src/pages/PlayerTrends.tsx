import { useEffect, useMemo, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend } from 'recharts'
import { PlayerSearch } from '../components/PlayerSearch'

function computeRolling(data: any[], key: string, n: number) {
  const out: any[] = []
  let sum = 0
  for (let i = 0; i < data.length; i++) {
    sum += data[i][key]
    if (i >= n) sum -= data[i - n][key]
    out.push({ ...data[i], [key + '_roll' + n]: i + 1 >= n ? sum / n : null })
  }
  return out
}

export default function PlayerTrends() {
  const [player, setPlayer] = useState<{ id: number; name: string } | null>(null)
  const [logs, setLogs] = useState<any[]>([])
  const [season, setSeason] = useState<string>('')

  useEffect(() => {
    (async () => {
      if (!player?.id) { setLogs([]); return }
      const qs = season ? `?season=${encodeURIComponent(season)}` : ''
      const res = await fetch(`/api/v1/players/${player.id}/gamelogs${qs}`)
      const data = await res.json()
      const items = (data.items || []).slice().reverse()
      const withRoll = ['pts','reb','ast','tpm'].reduce((acc, k) => computeRolling(acc, k, 5), items)
      const withRoll10 = ['pts','reb','ast','tpm'].reduce((acc, k) => computeRolling(acc, k, 10), withRoll)
      setLogs(withRoll10)
    })()
  }, [player, season])

  const chartData = useMemo(() => logs.map((g, idx) => ({
    idx,
    date: g.date,
    PTS: g.pts, REB: g.reb, AST: g.ast, '3PM': g.tpm,
    PTS5: g.pts_roll5, REB5: g.reb_roll5, AST5: g.ast_roll5, '3PM5': g.tpm_roll5,
    PTS10: g.pts_roll10, REB10: g.reb_roll10, AST10: g.ast_roll10, '3PM10': g.tpm_roll10,
  })), [logs])

  function Chart({ keys, title }: { keys: string[], title: string }) {
    return (
      <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, background: '#fff' }}>
        <div style={{ marginBottom: 8, fontWeight: 600 }}>{title}</div>
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" hide />
              <YAxis allowDecimals />
              <Tooltip />
              <Legend />
              {keys.map((k, i) => (
                <Line key={k} type="monotone" dataKey={k} stroke={["#111827","#2563eb","#059669","#b91c1c","#7c3aed"][i % 5]} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: 16 }}>
      <h2>Player Trends</h2>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <PlayerSearch onSelect={setPlayer} />
        <input value={season} onChange={(e) => setSeason(e.target.value)} placeholder="Season (e.g. 2024-25)" style={{ padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }} />
      </div>
      {player && (
        <div style={{ marginTop: 16, display: 'grid', gap: 12 }}>
          <Chart keys={["PTS","PTS5","PTS10"]} title="Points (game, 5g, 10g)" />
          <Chart keys={["REB","REB5","REB10"]} title="Rebounds (game, 5g, 10g)" />
          <Chart keys={["AST","AST5","AST10"]} title="Assists (game, 5g, 10g)" />
          <Chart keys={["3PM","3PM5","3PM10"]} title="3PM (game, 5g, 10g)" />
        </div>
      )}
    </div>
  )
}
