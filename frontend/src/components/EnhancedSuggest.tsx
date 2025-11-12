import { SuggestionCards } from './SuggestionCards'
import type { Player, PropSuggestionsResponse } from '../types/api'

export function EnhancedSuggest({ player, result }: { 
  player: Player | null
  result?: PropSuggestionsResponse
}) {
  return (
    <div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-4 transition-colors duration-200">Analysis Results</h3>
      
      <div className="space-y-4">
        {!player || !player.id ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400 transition-colors duration-200">
            <p className="text-sm">Select a player to view analysis results</p>
          </div>
        ) : result?.error ? (
          <div className="text-center py-8">
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 transition-colors duration-200">
              <p className="text-sm text-red-800 dark:text-red-300 font-medium mb-1 transition-colors duration-200">Error evaluating prop</p>
              <p className="text-xs text-red-600 dark:text-red-400 transition-colors duration-200">{result.error}</p>
            </div>
          </div>
        ) : result?.loading ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400 transition-colors duration-200">
            <p className="text-sm">Evaluating...</p>
          </div>
        ) : result && result.suggestions && result.suggestions.length > 0 ? (
          <SuggestionCards suggestions={result.suggestions || []} />
        ) : result && result.suggestions && result.suggestions.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400 transition-colors duration-200">
            <p className="text-sm">No results found. Please check your market lines and try again.</p>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400 transition-colors duration-200">
            <p className="text-sm">Enter market lines and click "Evaluate" to see analysis results</p>
          </div>
        )}
      </div>

      {/* View Profile Link */}
      {player?.id && (
        <div className="mt-6 pt-4 border-t border-gray-200 dark:border-slate-700 transition-colors duration-200">
          <a
            href={`/player/${player.id}`}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-700 dark:bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-800 dark:hover:bg-blue-700 transition-all shadow-sm border-2 border-blue-800 dark:border-blue-700 no-underline transition-colors duration-200"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
            View {player.name}'s Profile
          </a>
        </div>
      )}
    </div>
  )
}
