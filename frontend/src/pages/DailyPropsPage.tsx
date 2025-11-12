import { useQuery } from '@tanstack/react-query'
import { SuggestionCards } from '../components/SuggestionCards'

async function fetchDaily(minConfidence?: number) {
  const url = minConfidence ? `/api/v1/props/daily?min_confidence=${minConfidence}` : '/api/v1/props/daily'
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to load')
  return res.json()
}

export default function DailyPropsPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ['daily-props'], queryFn: () => fetchDaily(65) })
  if (isLoading) return (
    <div className="p-4 sm:p-6 md:p-8">
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
        <p className="mt-4 text-gray-600 dark:text-gray-400">Loading props...</p>
      </div>
    </div>
  )
  if (error) return (
    <div className="p-4 sm:p-6 md:p-8">
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <h3 className="text-red-800 dark:text-red-200 font-semibold mb-2">Error Loading Props</h3>
        <p className="text-red-600 dark:text-red-300 text-sm">{error instanceof Error ? error.message : 'Failed to load props'}</p>
      </div>
    </div>
  )
  const items = (data as any)?.items ?? []
  return (
    <div className="p-4 sm:p-6 md:p-8">
      <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-slate-100 mb-4 transition-colors duration-200">Today's Props</h2>
      {items.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-6 text-center transition-colors duration-200">
          <p className="text-gray-600 dark:text-gray-400">No suggestions available.</p>
        </div>
      ) : (
        <SuggestionCards suggestions={items} />
      )}
    </div>
  )
}
