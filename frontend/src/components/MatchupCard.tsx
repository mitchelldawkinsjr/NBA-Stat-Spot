export function MatchupCard({ title, stats, tags }: { title: string; stats: Array<{ label: string; value: string; valueColor?: string }>; tags?: string[] }) {
  return (
    <div className="bg-surface-container border border-outline/20 rounded-lg p-4 shadow-sm transition-colors duration-200">
      <div className="font-semibold text-on-surface mb-3 transition-colors duration-200">{title}</div>
      <div className="space-y-2 text-sm">
        {stats.map((s, i) => (
          <div key={i} className="flex items-center justify-between">
            <span className="text-on-surface-variant transition-colors duration-200">{s.label}</span>
            <span className={`font-semibold transition-colors duration-200 ${s.valueColor || 'text-on-surface'}`}>{s.value}</span>
          </div>
        ))}
      </div>
      {Array.isArray(tags) && tags.length > 0 && (
        <div className="mt-3 pt-3 border-t border-outline/20 flex flex-wrap gap-2 transition-colors duration-200">
          {tags.map((t, i) => (
            <span key={i} className="bg-surface-container-high text-on-surface text-xs font-bold px-2 py-1 rounded-full transition-colors duration-200">{t}</span>
          ))}
        </div>
      )}
    </div>
  )
}


