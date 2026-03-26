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
    <div className="rounded-xl bg-surface-container shadow-sm ring-1 ring-outline/20">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 px-3 sm:px-4 py-2 sm:py-3">
        {caption && (
          <div className="text-xs sm:text-sm font-semibold text-on-surface">{caption}</div>
        )}
        <div className="flex items-center gap-2">
          <span className="text-[10px] sm:text-xs text-on-surface-variant">Rows</span>
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
            className="px-2 pr-6 sm:pr-8 py-1 sm:py-1.5 rounded-md border border-outline/30 text-[10px] sm:text-xs bg-surface-container-high text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            {pageSizeOptions.map(opt => (<option key={opt} value={opt}>{opt}</option>))}
          </select>
        </div>
      </div>

      {/* Scrollable table */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs sm:text-sm">
          <thead className={`${stickyHeader ? 'sticky top-0 z-10' : ''} bg-surface-container-high border-b border-outline/20`}>
            <tr>
              {columns.map(col => (
                <th
                  key={col.key}
                  scope="col"
                  className={`px-3 sm:px-4 py-2 sm:py-3 text-[10px] sm:text-[11px] font-semibold uppercase tracking-wide text-on-surface-variant whitespace-nowrap ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                >
                  <button
                    onClick={() => toggleSort(col.key)}
                    className="inline-flex items-center gap-1 hover:text-on-surface transition-colors"
                  >
                    <span>{col.header}</span>
                    <SortIcon active={sortKey === col.key} dir={sortDir} />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-outline/10">
            {visible.map((row, idx) => (
              <tr
                key={idx}
                className={idx % 2 === 0 ? 'bg-surface-container' : 'bg-surface-container-low'}
              >
                {columns.map(col => (
                  <td
                    key={col.key}
                    className={`px-3 sm:px-4 py-2 sm:py-2.5 text-on-surface whitespace-nowrap ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                  >
                    {row[col.key] as ReactNode}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-2 px-3 sm:px-4 py-2 sm:py-3 border-t border-outline/20 text-[10px] sm:text-xs text-on-surface-variant">
        <div>Page {currentPage} of {totalPages}</div>
        <div className="flex items-center gap-1">
          {[
            { label: '« First', action: () => setPage(1), disabled: currentPage === 1 },
            { label: '‹ Prev', action: () => setPage(p => Math.max(1, p - 1)), disabled: currentPage === 1 },
            { label: 'Next ›', action: () => setPage(p => Math.min(totalPages, p + 1)), disabled: currentPage === totalPages },
            { label: 'Last »', action: () => setPage(totalPages), disabled: currentPage === totalPages },
          ].map(({ label, action, disabled }) => (
            <button
              key={label}
              onClick={action}
              disabled={disabled}
              className="px-1.5 sm:px-2 py-1 rounded-md border border-outline/20 bg-surface-container-high text-on-surface disabled:opacity-40 hover:bg-surface-container-highest transition-colors text-[10px] sm:text-xs"
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function SortIcon({ active, dir }: { active: boolean; dir: 'asc' | 'desc' }) {
  return (
    <svg
      className={`h-3.5 w-3.5 transition-colors ${active ? 'text-on-surface' : 'text-on-surface-variant/40'}`}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
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
  try { return JSON.stringify(v).length } catch { return '' }
}
