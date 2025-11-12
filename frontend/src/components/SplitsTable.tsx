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
    if (h === 'blue') return 'bg-blue-50/50 dark:bg-blue-900/20'
    if (h === 'green') return 'bg-green-50/50 dark:bg-green-900/20'
    if (h === 'purple') return 'bg-purple-50/50 dark:bg-purple-900/20'
    return ''
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm transition-colors duration-200">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-700">
        <thead className="bg-gray-50 dark:bg-slate-700 transition-colors duration-200">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">Split</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">Games</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">MIN</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">PTS</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">AST</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">REB</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">3PM</th>
            <th className="px-4 py-2 text-left text-xs font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">PRA</th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-slate-800 divide-y divide-gray-100 dark:divide-slate-700 transition-colors duration-200">
          {rows.map((r, i) => (
            <tr key={i} className={`${rowClass(r.highlight)} hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors duration-200`}>
              <td className="px-4 py-2 text-sm font-semibold text-gray-800 dark:text-slate-200 transition-colors duration-200">{r.label}</td>
              <td className="px-4 py-2 text-sm text-gray-700 dark:text-slate-300 transition-colors duration-200">{r.games}</td>
              <td className="px-4 py-2 text-sm text-gray-900 dark:text-slate-100 transition-colors duration-200">{r.minutes.toFixed(1)}</td>
              <td className="px-4 py-2 text-sm text-gray-900 dark:text-slate-100 transition-colors duration-200">{r.pts.toFixed(1)}</td>
              <td className="px-4 py-2 text-sm text-gray-900 dark:text-slate-100 transition-colors duration-200">{r.ast.toFixed(1)}</td>
              <td className="px-4 py-2 text-sm text-gray-900 dark:text-slate-100 transition-colors duration-200">{r.reb.toFixed(1)}</td>
              <td className="px-4 py-2 text-sm text-gray-900 dark:text-slate-100 transition-colors duration-200">{r.threes.toFixed(1)}</td>
              <td className="px-4 py-2 text-sm text-gray-900 dark:text-slate-100 transition-colors duration-200">{r.pra.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


