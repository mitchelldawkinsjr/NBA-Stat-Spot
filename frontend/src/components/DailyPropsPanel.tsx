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
  const [pageSize, setPageSize] = useState<number>(10) // Default to 10 items per page
  
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
  
  // Reset to page 1 when page size changes
  useEffect(() => {
    setPage(1)
  }, [pageSize])

  const items = (data?.items ?? []) as any[]
  
  // Client-side filtering - all data is loaded
  const filtered = useMemo(() => {
    // First filter by date to ensure we only show props for today
    const todayItems = items.filter((item) => {
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
    const avg = count ? Math.round(filtered.reduce((a: number, b) => a + (b.confidence ?? 0), 0) / count) : 0
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
    <div className="border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 p-2.5 sm:p-3 transition-colors duration-200">
      <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
        <div className="text-sm font-semibold text-gray-800 dark:text-slate-100 transition-colors duration-200">Daily Props</div>
        <div className="flex gap-1.5 sm:gap-2 items-center flex-wrap">
          <select value={type} onChange={(e) => setType(e.target.value as TypeFilter)} className="text-[10px] sm:text-xs px-1.5 sm:px-2 pr-6 sm:pr-8 py-1 border border-gray-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 transition-colors duration-200">
            {TYPES.map((t) => <option key={t} value={t} className="bg-white dark:bg-slate-700">{t}</option>)}
          </select>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search" className="text-[10px] sm:text-xs px-1.5 sm:px-2 py-1 border border-gray-300 dark:border-slate-600 rounded w-20 sm:w-24 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 placeholder-gray-400 dark:placeholder-gray-500 transition-colors duration-200" />
          <div title="Minimum confidence threshold" className="flex items-center gap-1">
            <span className="text-[10px] text-gray-600 dark:text-gray-400 transition-colors duration-200">Min:</span>
            <input type="range" min={45} max={75} step={1} value={minConf} onChange={(e) => setMinConf(Number(e.target.value))} className="w-12 sm:w-16" />
            <span className="text-[10px] sm:text-xs font-semibold w-8 text-right text-gray-900 dark:text-slate-100 transition-colors duration-200">{minConf}%</span>
          </div>
        </div>
      </div>
      
      {/* Stats Strip - Shows stats for the filtered data */}
      <div className="overflow-x-auto -mx-2.5 px-2.5 mt-2 mb-2">
        <div className="flex gap-1.5 min-w-max">
          <div className="flex-shrink-0 bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded p-1.5 shadow-sm min-w-[70px] transition-colors duration-200">
            <div className="text-[9px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 transition-colors duration-200">Count</div>
            <div className="text-base sm:text-lg font-extrabold text-blue-900 dark:text-blue-300 transition-colors duration-200">{stats.count}</div>
          </div>
          <div className="flex-shrink-0 bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded p-1.5 shadow-sm min-w-[70px] transition-colors duration-200">
            <div className="text-[9px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 transition-colors duration-200">Avg</div>
            <div className="text-base sm:text-lg font-extrabold text-blue-900 dark:text-blue-300 transition-colors duration-200">{stats.avg}%</div>
          </div>
          <div className="flex-shrink-0 bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded p-1.5 shadow-sm min-w-[70px] transition-colors duration-200">
            <div className="text-[9px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 transition-colors duration-200">Top</div>
            <div className="text-base sm:text-lg font-extrabold text-blue-900 dark:text-blue-300 transition-colors duration-200">{stats.top}%</div>
          </div>
        </div>
      </div>

      <div className="mt-2">
        {isLoading ? (
          <div className="py-8">
            <LoadingSpinner message="Loading daily props..." size="md" />
          </div>
        ) : error ? (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-800 dark:text-red-300 transition-colors duration-200">
            <p className="font-medium">Error loading props</p>
            {error instanceof Error && <p className="text-xs mt-1">{error.message}</p>}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-6 text-center bg-gray-50 dark:bg-slate-700/50 rounded-lg border border-gray-200 dark:border-slate-600 transition-colors duration-200">
            <p className="text-gray-600 dark:text-gray-400 font-medium transition-colors duration-200">No suggestions available.</p>
            <p className="text-xs mt-1 text-gray-500 dark:text-gray-500 transition-colors duration-200">Try adjusting your filters</p>
          </div>
        ) : (
          <div className="w-full">
            {/* Grid container with responsive columns - displays results in a grid format */}
            <SuggestionCards suggestions={paginatedItems} horizontal={false} />
          </div>
        )}
      </div>
      
      {/* Pagination Controls */}
      {!isLoading && !error && filtered.length > 0 && (
        <div className="mt-4 flex items-center justify-between gap-2 flex-wrap pt-3 border-t border-gray-200 dark:border-slate-700 transition-colors duration-200">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">
              Showing {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, totalItems)} of {totalItems}
            </div>
            <div className="flex items-center gap-1.5">
              <label className="text-[10px] text-gray-600 dark:text-gray-400 transition-colors duration-200">Per page:</label>
              <select 
                value={pageSize} 
                onChange={(e) => setPageSize(Number(e.target.value))}
                className="text-[10px] sm:text-xs px-1.5 sm:px-2 pr-6 sm:pr-8 py-1 border border-gray-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 transition-colors duration-200"
              >
                <option value={10} className="bg-white dark:bg-slate-700">10</option>
                <option value={20} className="bg-white dark:bg-slate-700">20</option>
                <option value={30} className="bg-white dark:bg-slate-700">30</option>
                <option value={50} className="bg-white dark:bg-slate-700">50</option>
                <option value={100} className="bg-white dark:bg-slate-700">100</option>
              </select>
            </div>
          </div>
          {totalPages > 1 && (
            <div className="flex gap-2 items-center">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={!hasPrev || isLoading}
                className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors duration-200 ${
                  hasPrev && !isLoading
                    ? 'bg-white dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-100 hover:bg-gray-50 dark:hover:bg-slate-600 cursor-pointer'
                    : 'bg-gray-100 dark:bg-slate-700/50 border-gray-200 dark:border-slate-600 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                }`}
              >
                Previous
              </button>
              <div className="text-xs text-gray-700 dark:text-gray-300 px-2 transition-colors duration-200">
                Page {page} of {totalPages}
              </div>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={!hasNext || isLoading}
                className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors duration-200 ${
                  hasNext && !isLoading
                    ? 'bg-white dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-100 hover:bg-gray-50 dark:hover:bg-slate-600 cursor-pointer'
                    : 'bg-gray-100 dark:bg-slate-700/50 border-gray-200 dark:border-slate-600 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                }`}
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


