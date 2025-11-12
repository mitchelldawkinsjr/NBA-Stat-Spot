export function MatchupCard({ title, stats, tags }: { title: string; stats: Array<{ label: string; value: string; valueColor?: string }>; tags?: string[] }) {
  return (
    <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg p-4 shadow-sm transition-colors duration-200">
      <div className="font-semibold text-gray-900 dark:text-slate-100 mb-3 transition-colors duration-200">{title}</div>
      <div className="space-y-2 text-sm">
        {stats.map((s, i) => (
          <div key={i} className="flex items-center justify-between">
            <span className="text-gray-600 dark:text-gray-400 transition-colors duration-200">{s.label}</span>
            <span className={`font-semibold transition-colors duration-200 ${s.valueColor || 'text-gray-900 dark:text-slate-100'}`}>{s.value}</span>
          </div>
        ))}
      </div>
      {Array.isArray(tags) && tags.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-slate-700 flex flex-wrap gap-2 transition-colors duration-200">
          {tags.map((t, i) => (
            <span key={i} className="bg-gray-100 dark:bg-slate-700 text-gray-800 dark:text-slate-200 text-xs font-bold px-2 py-1 rounded-full transition-colors duration-200">{t}</span>
          ))}
        </div>
      )}
    </div>
  )
}


