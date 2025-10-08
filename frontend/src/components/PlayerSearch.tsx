import { useState, useEffect } from 'react'

export function PlayerSearch({ onSelect }: { onSelect: (p: { id: number; name: string }) => void }) {
  const [q, setQ] = useState('')
  const [items, setItems] = useState<any[]>([])

  useEffect(() => {
    const c = setTimeout(async () => {
      if (!q) { setItems([]); return }
      const res = await fetch(`/api/players/search?q=${encodeURIComponent(q)}`)
      const data = await res.json()
      setItems(data.items || [])
    }, 250)
    return () => clearTimeout(c)
  }, [q])

  return (
    <div>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search player…" />
      {items.length > 0 && (
        <ul style={{ border: '1px solid #eee', padding: 8 }}>
          {items.map((p) => (
            <li key={p.id}>
              <button onClick={() => onSelect(p)}>{p.name}</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
