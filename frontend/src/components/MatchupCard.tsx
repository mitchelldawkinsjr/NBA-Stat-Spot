export function MatchupCard({ title, stats, tags }: { title: string; stats: Array<{ label: string; value: string; valueColor?: string }>; tags?: string[] }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <div className="font-semibold text-gray-900 mb-3">{title}</div>
      <div className="space-y-2 text-sm">
        {stats.map((s, i) => (
          <div key={i} className="flex items-center justify-between">
            <span className="text-gray-600">{s.label}</span>
            <span className={`font-semibold ${s.valueColor || 'text-gray-900'}`}>{s.value}</span>
          </div>
        ))}
      </div>
      {Array.isArray(tags) && tags.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100 flex flex-wrap gap-2">
          {tags.map((t, i) => (
            <span key={i} className="bg-gray-100 text-gray-800 text-xs font-bold px-2 py-1 rounded-full">{t}</span>
          ))}
        </div>
      )}
    </div>
  )
}


