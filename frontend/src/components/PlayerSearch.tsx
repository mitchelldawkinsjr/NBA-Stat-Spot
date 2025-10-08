import { useState, useEffect } from 'react'

export function PlayerSearch({ onSelect }: { onSelect: (p: { id: number; name: string }) => void }) {
  const [q, setQ] = useState('')
  const [items, setItems] = useState<any[]>([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const c = setTimeout(async () => {
      if (!q || items.length === 0 && !open) {
        // fetch when typing
      }
      if (!q) { setItems([]); return }
      const res = await fetch(`/api/players/search?q=${encodeURIComponent(q)}`)
      const data = await res.json()
      setItems(data.items || [])
      setOpen(true)
    }, 250)
    return () => clearTimeout(c)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q])

  function handleSelect(p: any) {
    setQ(p.name)
    setItems([])
    setOpen(false)
    onSelect(p)
  }

  function clear() {
    setQ('')
    setItems([])
    setOpen(false)
    onSelect({ id: 0, name: '' })
  }

  return (
    <div style={{ position: 'relative', maxWidth: 420 }}>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search player…"
          style={{ flex: 1, padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }}
        />
        {q && (
          <button onClick={clear} style={{ padding: '8px 12px' }}>Clear</button>
        )}
      </div>
      {open && items.length > 0 && (
        <ul style={{ position: 'absolute', zIndex: 10, background: '#fff', boxShadow: '0 4px 16px rgba(0,0,0,0.08)', listStyle: 'none', padding: 8, margin: 4, width: '100%', borderRadius: 8, border: '1px solid #eee', maxHeight: 280, overflowY: 'auto' }}>
          {items.map((p) => (
            <li key={p.id}>
              <button onClick={() => handleSelect(p)} style={{ width: '100%', textAlign: 'left', padding: '8px 10px', border: 'none', background: 'transparent', cursor: 'pointer' }}>
                {p.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
