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
      <div className="border border-gray-200 dark:border-slate-700 rounded-lg p-3 bg-white dark:bg-slate-800 transition-colors duration-200">
        <div className="mb-2 font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">{title}</div>
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-slate-700" />
              <XAxis dataKey="date" hide stroke="#6b7280" className="dark:stroke-slate-400" />
              <YAxis allowDecimals stroke="#6b7280" className="dark:stroke-slate-400" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'var(--panel-bg)', 
                  border: '1px solid var(--panel-border)',
                  borderRadius: '6px'
                }}
                labelStyle={{ color: 'var(--chart-primary)' }}
              />
              <Legend wrapperStyle={{ color: 'var(--chart-primary)' }} />
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
    <div className="p-4 sm:p-6 md:p-8">
      <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-slate-100 mb-4 transition-colors duration-200">Player Trends</h2>
      <div className="flex flex-wrap gap-3 items-center mb-3">
        <PlayerSearch onSelect={setPlayer} />
        <input 
          value={season} 
          onChange={(e) => setSeason(e.target.value)} 
          placeholder="Season (e.g. 2024-25)" 
          className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-600/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
        />
      </div>
      <div className="text-xs text-gray-600 dark:text-gray-400 mb-4 transition-colors duration-200">Rolling averages: 5-game and 10-game overlays for quick trend reading.</div>
      {player && (
        <div className="grid gap-3 mt-4">
          <Chart keys={["PTS","PTS5","PTS10"]} title="Points (game, 5g, 10g)" />
          <Chart keys={["REB","REB5","REB10"]} title="Rebounds (game, 5g, 10g)" />
          <Chart keys={["AST","AST5","AST10"]} title="Assists (game, 5g, 10g)" />
          <Chart keys={["3PM","3PM5","3PM10"]} title="3PM (game, 5g, 10g)" />
        </div>
      )}
    </div>
  )
}
