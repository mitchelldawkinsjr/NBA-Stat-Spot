import type { ReactNode } from 'react'
import { useMemo, useState } from 'react'

type Align = 'left' | 'right'

export type DataTableColumn<Row extends Record<string, unknown>> = {
  key: keyof Row & string
  header: string
  align?: Align
}

export type DataTableProps<Row extends Record<string, unknown>> = {
  columns: Array<DataTableColumn<Row>>
  rows: Row[]
  initialSort?: { key: keyof Row & string; direction: 'asc' | 'desc' }
  pageSizeOptions?: number[]
  defaultPageSize?: number
  stickyHeader?: boolean
  caption?: string
}

export function DataTable<Row extends Record<string, unknown>>({
  columns,
  rows,
  initialSort,
  pageSizeOptions = [10, 20, 50],
  defaultPageSize = 10,
  stickyHeader = true,
  caption,
}: DataTableProps<Row>) {
  const [sortKey, setSortKey] = useState<string | null>(initialSort?.key ?? null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>(initialSort?.direction ?? 'asc')
  const [pageSize, setPageSize] = useState<number>(defaultPageSize)
  const [page, setPage] = useState<number>(1)

  const sorted = useMemo(() => {
    if (!sortKey) return rows
    const copy = [...rows]
    copy.sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      const aVal = valueForSort(av)
      const bVal = valueForSort(bv)
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1
      return 0
    })
    return copy
  }, [rows, sortKey, sortDir])

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const currentPage = Math.min(page, totalPages)
  const startIdx = (currentPage - 1) * pageSize
  const visible = sorted.slice(startIdx, startIdx + pageSize)

  function toggleSort(key: string) {
    if (sortKey !== key) {
      setSortKey(key)
      setSortDir('asc')
    } else {
      setSortDir(prev => (prev === 'asc' ? 'desc' : 'asc'))
    }
  }

  return (
    <div className="rounded-xl sm:rounded-2xl bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 transition-colors duration-200">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 px-3 sm:px-4 py-2 sm:py-3">
        {caption && <div className="text-xs sm:text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">{caption}</div>}
        <div className="flex items-center gap-2">
          <span className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">Rows</span>
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
            className="px-2 pr-6 sm:pr-8 py-1 sm:py-1.5 rounded-md border border-gray-300 dark:border-slate-600 text-[10px] sm:text-xs bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
          >
            {pageSizeOptions.map(opt => (<option key={opt} value={opt}>{opt}</option>))}
          </select>
        </div>
      </div>
      <div className="overflow-x-auto -mx-2 sm:mx-0">
        <table className="min-w-full text-xs sm:text-sm">
          <thead className={`${stickyHeader ? 'sticky top-0 z-10' : ''} bg-gray-50 dark:bg-slate-700 border-b border-gray-100 dark:border-slate-600 transition-colors duration-200`}>
            <tr>
              {columns.map(col => (
                <th key={col.key} scope="col" className={`px-2 sm:px-4 py-2 sm:py-3 text-[10px] sm:text-[11px] font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 ${col.align === 'right' ? 'text-right' : 'text-left'} transition-colors duration-200`}>
                  <button onClick={() => toggleSort(col.key)} className="inline-flex items-center gap-1 hover:text-gray-800 dark:hover:text-gray-200 transition-colors duration-200">
                    <span>{col.header}</span>
                    <SortIcon active={sortKey === col.key} dir={sortDir} />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-slate-700 transition-colors duration-200">
            {visible.map((row, idx) => (
              <tr key={idx} className={`${idx % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-gray-50 dark:bg-slate-700/50'} transition-colors duration-200`}>
                {columns.map(col => (
                  <td key={col.key} className={`px-2 sm:px-4 py-2 sm:py-2.5 ${col.align === 'right' ? 'text-right' : 'text-left'} text-gray-800 dark:text-slate-200 transition-colors duration-200`}>{row[col.key] as ReactNode}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-col sm:flex-row items-center justify-between gap-2 px-3 sm:px-4 py-2 sm:py-3 border-t border-gray-100 dark:border-slate-700 text-[10px] sm:text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">
        <div>Page {currentPage} of {totalPages}</div>
        <div className="flex items-center gap-1">
          <button onClick={() => setPage(1)} disabled={currentPage === 1} className="px-1.5 sm:px-2 py-1 rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 disabled:opacity-50 text-[10px] sm:text-xs transition-colors duration-200">« First</button>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} className="px-1.5 sm:px-2 py-1 rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 disabled:opacity-50 text-[10px] sm:text-xs transition-colors duration-200">‹ Prev</button>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} className="px-1.5 sm:px-2 py-1 rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 disabled:opacity-50 text-[10px] sm:text-xs transition-colors duration-200">Next ›</button>
          <button onClick={() => setPage(totalPages)} disabled={currentPage === totalPages} className="px-1.5 sm:px-2 py-1 rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 disabled:opacity-50 text-[10px] sm:text-xs transition-colors duration-200">Last »</button>
        </div>
      </div>
    </div>
  )
}

function SortIcon({ active, dir }: { active: boolean; dir: 'asc' | 'desc' }) {
  return (
    <svg className={`h-3.5 w-3.5 transition-colors duration-200 ${active ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500'}`} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      {dir === 'asc' ? (
        <path d="M7 14l5-5 5 5H7z" />
      ) : (
        <path d="M7 10l5 5 5-5H7z" />
      )}
    </svg>
  )
}

function valueForSort(v: unknown): number | string {
  if (v == null) return ''
  if (typeof v === 'number') return v
  if (typeof v === 'string') return v.toLowerCase()
  if (typeof v === 'boolean') return v ? 1 : 0
  // ReactNode or object – stringify length as a coarse fallback
  try { return JSON.stringify(v).length } catch { return '' }
}


