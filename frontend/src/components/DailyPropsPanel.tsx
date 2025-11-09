import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { SuggestionCards } from './SuggestionCards'
import { LoadingSpinner } from './LoadingSpinner'

const TYPES = ['All','PTS','REB','AST','3PM','PRA'] as const
type TypeFilter = typeof TYPES[number]

import { apiFetch } from '../utils/api'

async function fetchDaily(minConfidence?: number, date?: string) {
  // Fetch all data from API (no pagination - load everything)
  const params = new URLSearchParams()
  if (minConfidence) params.append('min_confidence', minConfidence.toString())
  if (date) params.append('date', date)
  const endpoint = `api/v1/props/daily${params.toString() ? '?' + params.toString() : ''}`
  const res = await apiFetch(endpoint)
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
  const [pageSize] = useState<number>(24) // Increased to show more items per page in grid
  
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
    <div className="border border-gray-200 rounded-lg bg-white p-2.5 sm:p-3">
      <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
        <div className="text-sm font-semibold text-gray-800">Daily Props</div>
        <div className="flex gap-1.5 sm:gap-2 items-center flex-wrap">
          <select value={type} onChange={(e) => setType(e.target.value as TypeFilter)} className="text-[10px] sm:text-xs px-1.5 sm:px-2 py-1 border border-gray-300 rounded bg-white">
            {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search" className="text-[10px] sm:text-xs px-1.5 sm:px-2 py-1 border border-gray-300 rounded w-20 sm:w-24" />
          <div title="Minimum confidence threshold" className="flex items-center gap-1">
            <span className="text-[10px] text-gray-600">Min:</span>
            <input type="range" min={45} max={75} step={1} value={minConf} onChange={(e) => setMinConf(Number(e.target.value))} className="w-12 sm:w-16" />
            <span className="text-[10px] sm:text-xs font-semibold w-8 text-right">{minConf}%</span>
          </div>
        </div>
      </div>
      
      {/* Stats Strip - Shows stats for the filtered data */}
      <div className="overflow-x-auto -mx-2.5 px-2.5 mt-2 mb-2">
        <div className="flex gap-1.5 min-w-max">
          <div className="flex-shrink-0 bg-gray-50 border border-gray-200 rounded p-1.5 shadow-sm min-w-[70px]">
            <div className="text-[9px] font-bold uppercase tracking-wide text-gray-500">Count</div>
            <div className="text-base sm:text-lg font-extrabold text-blue-900">{stats.count}</div>
          </div>
          <div className="flex-shrink-0 bg-gray-50 border border-gray-200 rounded p-1.5 shadow-sm min-w-[70px]">
            <div className="text-[9px] font-bold uppercase tracking-wide text-gray-500">Avg</div>
            <div className="text-base sm:text-lg font-extrabold text-blue-900">{stats.avg}%</div>
          </div>
          <div className="flex-shrink-0 bg-gray-50 border border-gray-200 rounded p-1.5 shadow-sm min-w-[70px]">
            <div className="text-[9px] font-bold uppercase tracking-wide text-gray-500">Top</div>
            <div className="text-base sm:text-lg font-extrabold text-blue-900">{stats.top}%</div>
          </div>
        </div>
      </div>

      <div className="mt-2">
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
          <div className="w-full">
            {/* Grid container with responsive columns - displays results in a grid format */}
            <SuggestionCards suggestions={paginatedItems} horizontal={false} />
          </div>
        )}
      </div>
      
      {/* Pagination Controls */}
      {!isLoading && !error && filtered.length > 0 && totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between gap-2 flex-wrap pt-3 border-t border-gray-200">
          <div className="text-xs text-gray-600">
            Showing {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, totalItems)} of {totalItems}
          </div>
          <div className="flex gap-2 items-center">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={!hasPrev || isLoading}
              className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                hasPrev && !isLoading
                  ? 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50 cursor-pointer'
                  : 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              Previous
            </button>
            <div className="text-xs text-gray-700 px-2">
              Page {page} of {totalPages}
            </div>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={!hasNext || isLoading}
              className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                hasNext && !isLoading
                  ? 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50 cursor-pointer'
                  : 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}


