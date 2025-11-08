import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { SuggestionCards } from './SuggestionCards'
import { LoadingSpinner } from './LoadingSpinner'

const TYPES = ['All','PTS','REB','AST','3PM','PRA'] as const
type TypeFilter = typeof TYPES[number]

async function fetchDaily(minConfidence?: number, date?: string) {
  // Fetch all data from API (no pagination - load everything)
  const params = new URLSearchParams()
  if (minConfidence) params.append('min_confidence', minConfidence.toString())
  if (date) params.append('date', date)
  const url = `/api/v1/props/daily${params.toString() ? '?' + params.toString() : ''}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to load')
  const data = await res.json()
  
  return data
}

export function DailyPropsPanel() {
  // Get today's date for filtering - use local date to match what user sees
  const today = new Date().toLocaleDateString('en-CA') // YYYY-MM-DD format in local timezone
  const [minConf, setMinConf] = useState<number>(50)
  const [type, setType] = useState<TypeFilter>('All')
  const [q, setQ] = useState<string>('')
  const [page, setPage] = useState<number>(1)
  const [pageSize] = useState<number>(20)
  
  const { data, isLoading, error } = useQuery({ 
    queryKey: ['daily-props', minConf, today], 
    queryFn: () => fetchDaily(minConf, today),
    staleTime: 30 * 60 * 1000, // 30 minutes - daily props only change once per day
    gcTime: 24 * 60 * 60 * 1000, // Keep in cache for 24 hours (entire day)
    refetchOnMount: false, // Use cache first, don't refetch on mount
    refetchOnWindowFocus: false, // Don't refetch when window gains focus
    refetchOnReconnect: false, // Don't refetch on reconnect
  })

  useEffect(() => { 
    setPage(1) // Reset to page 1 when filters change
    // Don't force refetch - let React Query handle it based on staleTime
  }, [minConf, today])
  
  // Reset to page 1 when search changes
  useEffect(() => {
    setPage(1)
  }, [q, type])

  const items = (data?.items ?? []) as any[]
  
  // Client-side filtering - all data is loaded
  const filtered = useMemo(() => {
    // First filter by date to ensure we only show props for today
    const todayItems = items.filter((item: any) => {
      const itemDate = item.gameDate || item.game_date
      // Must have a date and it must match today
      return itemDate && (itemDate === today || itemDate.startsWith(today))
    })
    // Then apply type and search filters
    return todayItems.filter((s) => (type === 'All' || s.type === type) && (!q || (s.playerName || '').toLowerCase().includes(q.toLowerCase())))
  }, [items, type, q, today])

  // Calculate stats from all filtered data (not just current page)
  const stats = useMemo(() => {
    const count = filtered.length
    const avg = count ? Math.round(filtered.reduce((a: number, b: any) => a + (b.confidence ?? 0), 0) / count) : 0
    const top = filtered.length > 0 && filtered[0]?.confidence ? Math.round(filtered[0].confidence) : 0
    return { count, avg, top }
  }, [filtered])
  
  // Client-side pagination on filtered results
  const totalItems = filtered.length
  const totalPages = Math.ceil(totalItems / pageSize)
  const hasNext = page < totalPages
  const hasPrev = page > 1
  
  // Get paginated slice of filtered items
  const paginatedItems = useMemo(() => {
    const startIdx = (page - 1) * pageSize
    const endIdx = startIdx + pageSize
    return filtered.slice(startIdx, endIdx)
  }, [filtered, page, pageSize])

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff', padding: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ fontWeight: 600 }}>Daily Props</div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <select value={type} onChange={(e) => setType(e.target.value as TypeFilter)} style={{ padding: '6px 8px', border: '1px solid #ddd', borderRadius: 6, background: '#fff' }}>
            {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search player" style={{ padding: '6px 8px', border: '1px solid #ddd', borderRadius: 6 }} />
          <div title="Minimum confidence threshold" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 12, color: '#6b7280' }}>Min Conf</span>
            <input type="range" min={45} max={75} step={1} value={minConf} onChange={(e) => setMinConf(Number(e.target.value))} />
            <span style={{ fontSize: 12 }}>{minConf}%</span>
          </div>
        </div>
      </div>
      
      {/* Stats Strip - Shows stats for the filtered data */}
      <div className="overflow-x-auto -mx-3 px-3 mt-3 mb-3">
        <div className="flex gap-2 min-w-max">
          <div className="flex-shrink-0 bg-gray-50 border border-gray-200 rounded-lg p-2 shadow-sm min-w-[100px]">
            <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500">Suggestions</div>
            <div className="text-xl font-extrabold text-blue-900">{stats.count}</div>
          </div>
          <div className="flex-shrink-0 bg-gray-50 border border-gray-200 rounded-lg p-2 shadow-sm min-w-[100px]">
            <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500">Avg Confidence</div>
            <div className="text-xl font-extrabold text-blue-900">{stats.avg}%</div>
          </div>
          <div className="flex-shrink-0 bg-gray-50 border border-gray-200 rounded-lg p-2 shadow-sm min-w-[100px]">
            <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500">Top Confidence</div>
            <div className="text-xl font-extrabold text-blue-900">{stats.top}%</div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 10 }}>
        {isLoading ? (
          <div className="py-8">
            <LoadingSpinner message="Loading daily props..." size="md" />
          </div>
        ) : error ? (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            <p className="font-medium">Error loading props</p>
            {error instanceof Error && <p className="text-xs mt-1">{error.message}</p>}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-6 text-center bg-gray-50 rounded-lg border border-gray-200">
            <p className="text-gray-600 font-medium">No suggestions available.</p>
            <p className="text-xs mt-1 text-gray-500">Try adjusting your filters</p>
          </div>
        ) : (
          <SuggestionCards suggestions={paginatedItems} />
        )}
      </div>
      
      {/* Pagination Controls */}
      {!isLoading && !error && filtered.length > 0 && totalPages > 1 && (
        <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
          <div style={{ fontSize: 12, color: '#6b7280' }}>
            Showing {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, totalItems)} of {totalItems}
          </div>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={!hasPrev || isLoading}
              style={{
                padding: '6px 12px',
                border: '1px solid #d1d5db',
                borderRadius: 6,
                background: hasPrev && !isLoading ? '#fff' : '#f3f4f6',
                color: hasPrev && !isLoading ? '#374151' : '#9ca3af',
                cursor: hasPrev && !isLoading ? 'pointer' : 'not-allowed',
                fontSize: 12,
                fontWeight: 500
              }}
            >
              Previous
            </button>
            <div style={{ fontSize: 12, color: '#374151', padding: '0 8px' }}>
              Page {page} of {totalPages}
            </div>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={!hasNext || isLoading}
              style={{
                padding: '6px 12px',
                border: '1px solid #d1d5db',
                borderRadius: 6,
                background: hasNext && !isLoading ? '#fff' : '#f3f4f6',
                color: hasNext && !isLoading ? '#374151' : '#9ca3af',
                cursor: hasNext && !isLoading ? 'pointer' : 'not-allowed',
                fontSize: 12,
                fontWeight: 500
              }}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}


