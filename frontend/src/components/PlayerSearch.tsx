import { useState, useEffect, useRef } from 'react'
import { apiFetch } from '../utils/api'

export function PlayerSearch({ onSelect }: { onSelect: (p: { id: number; name: string }) => void }) {
  const [q, setQ] = useState('')
  const [items, setItems] = useState<any[]>([])
  const [open, setOpen] = useState(false)
  const isSelectingRef = useRef(false)

  useEffect(() => {
    // Don't search if we're in the middle of selecting a player
    if (isSelectingRef.current) {
      return
    }
    
    const c = setTimeout(async () => {
      if (!q) { 
        setItems([])
        setOpen(false)
        return 
      }
      const res = await apiFetch(`api/v1/players/search?q=${encodeURIComponent(q)}`)
      const data = await res.json()
      setItems(data.items || [])
      setOpen(true)
    }, 250)
    return () => clearTimeout(c)
  }, [q])

  function handleSelect(p: any) {
    isSelectingRef.current = true
    setQ(p.name)
    setItems([])
    setOpen(false)
    onSelect(p)
    // Reset the flag after a short delay to allow the state to settle
    setTimeout(() => {
      isSelectingRef.current = false
    }, 100)
  }

  function clear() {
    setQ('')
    setItems([])
    setOpen(false)
    onSelect({ id: 0, name: '' })
  }

  return (
    <div className="relative max-w-[420px]">
      <div className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search player…"
          className="flex-1 px-2.5 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
        />
        {q && (
          <button 
            onClick={clear} 
            className="px-3 py-2 text-sm text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-md hover:bg-gray-50 dark:hover:bg-slate-600 transition-colors duration-200"
          >
            Clear
          </button>
        )}
      </div>
      {open && items.length > 0 && (
        <ul 
          onMouseDown={(e: any) => e.preventDefault()} 
          onClick={(e: any) => e.preventDefault()}
          className="absolute z-10 bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-100 shadow-lg list-none p-2 m-1 w-full rounded-lg border border-gray-200 dark:border-slate-700 max-h-[280px] overflow-y-auto transition-colors duration-200"
        >
          {items.map((p) => (
            <li key={p.id}>
              <button
                onClick={(e: any) => {
                  e.preventDefault()
                  e.stopPropagation()
                  handleSelect(p)
                }}
                onMouseDown={(e: any) => {
                  e.preventDefault()
                  e.stopPropagation()
                }}
                type="button" 
                className="w-full text-left px-2.5 py-2 border-none bg-transparent hover:bg-gray-100 dark:hover:bg-slate-700 cursor-pointer text-gray-900 dark:text-slate-100 rounded-md transition-colors duration-200"
              >
                {p.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
