import { useState, useEffect } from 'react'

type Team = {
  id: number
  full_name: string
  abbreviation: string
  city: string
  nickname: string
  conference?: string
  division?: string
}

export function TeamSearch({ onSelect }: { onSelect: (t: Team | null) => void }) {
  const [q, setQ] = useState('')
  const [items, setItems] = useState<Team[]>([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const c = setTimeout(async () => {
      if (!q) { setItems([]); setOpen(false); return }
      try {
        const res = await fetch(`/api/v1/teams`)
        if (!res.ok) return
        const data = await res.json()
        const allTeams = (data.items || []) as Team[]
        const filtered = allTeams.filter(t => 
          t.full_name.toLowerCase().includes(q.toLowerCase()) ||
          t.abbreviation.toLowerCase().includes(q.toLowerCase()) ||
          t.city.toLowerCase().includes(q.toLowerCase())
        ).slice(0, 10)
        setItems(filtered)
        setOpen(true)
      } catch (e) {
        console.error('Failed to search teams:', e)
      }
    }, 250)
    return () => clearTimeout(c)
  }, [q])

  function handleSelect(t: Team) {
    setQ(t.abbreviation || t.full_name)
    setItems([])
    setOpen(false)
    onSelect(t)
  }

  function clear() {
    setQ('')
    setItems([])
    setOpen(false)
    onSelect(null)
  }

  return (
    <div className="relative max-w-[420px]">
      <div className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search team (e.g. Lakers, LAL)…"
          className="flex-1 px-2.5 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
        />
        {q && (
          <button onClick={clear} className="px-3 py-2 text-sm text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-md hover:bg-gray-50 dark:hover:bg-slate-600 transition-colors duration-200">Clear</button>
        )}
      </div>
      {open && items.length > 0 && (
        <ul onMouseDown={(e: any) => e.preventDefault()} className="absolute z-10 bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-100 shadow-lg list-none p-2 m-1 w-full rounded-lg border border-gray-200 dark:border-slate-700 max-h-[280px] overflow-y-auto transition-colors duration-200">
          {items.map((t) => (
            <li key={t.id}>
              <button
                onPointerDown={(e: any) => { e.preventDefault(); handleSelect(t); }}
                type="button" 
                className="w-full text-left px-2.5 py-2 border-none bg-transparent hover:bg-gray-100 dark:hover:bg-slate-700 cursor-pointer text-gray-900 dark:text-slate-100 rounded-md transition-colors duration-200"
              >
                <div className="font-medium">{t.abbreviation} - {t.full_name}</div>
                {t.conference && <div className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">{t.conference} • {t.division}</div>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

