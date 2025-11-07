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
    <div style={{ position: 'relative', maxWidth: 420 }}>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search team (e.g. Lakers, LAL)…"
          style={{ flex: 1, padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }}
        />
        {q && (
          <button onClick={clear} style={{ padding: '8px 12px' }}>Clear</button>
        )}
      </div>
      {open && items.length > 0 && (
        <ul onMouseDown={(e: any) => e.preventDefault()} style={{ position: 'absolute', zIndex: 10, background: '#fff', color: '#111827', boxShadow: '0 4px 16px rgba(0,0,0,0.08)', listStyle: 'none', padding: 8, margin: 4, width: '100%', borderRadius: 8, border: '1px solid #eee', maxHeight: 280, overflowY: 'auto' }}>
          {items.map((t) => (
            <li key={t.id}>
              <button
                onPointerDown={(e: any) => { e.preventDefault(); handleSelect(t); }}
                onMouseEnter={(e: any) => (e.currentTarget.style.background = '#f3f4f6')}
                onMouseLeave={(e: any) => (e.currentTarget.style.background = 'transparent')}
                type="button" style={{ width: '100%', textAlign: 'left', padding: '8px 10px', border: 'none', background: 'transparent', cursor: 'pointer', color: '#111827', borderRadius: 6 }}
              >
                <div className="font-medium">{t.abbreviation} - {t.full_name}</div>
                {t.conference && <div className="text-xs text-gray-500">{t.conference} • {t.division}</div>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

