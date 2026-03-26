type Row = {
  label: string
  games: number
  minutes: number
  pts: number
  ast: number
  reb: number
  threes: number
  pra: number
  highlight?: 'blue' | 'green' | 'purple'
}

export function SplitsTable({ rows }: { rows: Row[] }) {
  function rowHighlight(h?: Row['highlight']) {
    if (h === 'blue') return 'bg-blue-900/20'
    if (h === 'green') return 'bg-emerald-900/20'
    if (h === 'purple') return 'bg-purple-900/20'
    return ''
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-outline/20 bg-surface-container shadow-sm">
      <table className="min-w-full divide-y divide-outline/10">
        <thead className="bg-surface-container-high">
          <tr>
            {['Split', 'G', 'MIN', 'PTS', 'AST', 'REB', '3PM', 'PRA'].map(h => (
              <th
                key={h}
                className="px-3 py-2 text-left text-[10px] sm:text-xs font-bold text-on-surface-variant uppercase tracking-wider whitespace-nowrap"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-outline/10">
          {rows.map((r, i) => (
            <tr
              key={i}
              className={`hover:bg-surface-container-high transition-colors ${rowHighlight(r.highlight)}`}
            >
              <td className="px-3 py-2 text-xs sm:text-sm font-semibold text-on-surface whitespace-nowrap">{r.label}</td>
              <td className="px-3 py-2 text-xs sm:text-sm text-on-surface-variant whitespace-nowrap">{r.games}</td>
              <td className="px-3 py-2 text-xs sm:text-sm text-on-surface whitespace-nowrap">{r.minutes.toFixed(1)}</td>
              <td className="px-3 py-2 text-xs sm:text-sm text-on-surface whitespace-nowrap">{r.pts.toFixed(1)}</td>
              <td className="px-3 py-2 text-xs sm:text-sm text-on-surface whitespace-nowrap">{r.ast.toFixed(1)}</td>
              <td className="px-3 py-2 text-xs sm:text-sm text-on-surface whitespace-nowrap">{r.reb.toFixed(1)}</td>
              <td className="px-3 py-2 text-xs sm:text-sm text-on-surface whitespace-nowrap">{r.threes.toFixed(1)}</td>
              <td className="px-3 py-2 text-xs sm:text-sm text-on-surface whitespace-nowrap">{r.pra.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
