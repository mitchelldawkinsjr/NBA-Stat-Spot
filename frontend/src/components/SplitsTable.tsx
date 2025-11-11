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
  function rowClass(h?: Row['highlight']) {
    if (h === 'blue') return 'bg-blue-50/50'
    if (h === 'green') return 'bg-green-50/50'
    if (h === 'purple') return 'bg-purple-50/50'
    return ''
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">Split</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">Games</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">MIN</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">PTS</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">AST</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">REB</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">3PM</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">PRA</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {rows.map((r, i) => (
            <tr key={i} className={`${rowClass(r.highlight)} hover:bg-gray-50`}>
              <td className="px-4 py-2 text-sm font-semibold text-gray-800">{r.label}</td>
              <td className="px-4 py-2 text-sm text-gray-700">{r.games}</td>
              <td className="px-4 py-2 text-sm text-gray-900">{r.minutes.toFixed(1)}</td>
              <td className="px-4 py-2 text-sm text-gray-900">{r.pts.toFixed(1)}</td>
              <td className="px-4 py-2 text-sm text-gray-900">{r.ast.toFixed(1)}</td>
              <td className="px-4 py-2 text-sm text-gray-900">{r.reb.toFixed(1)}</td>
              <td className="px-4 py-2 text-sm text-gray-900">{r.threes.toFixed(1)}</td>
              <td className="px-4 py-2 text-sm text-gray-900">{r.pra.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


