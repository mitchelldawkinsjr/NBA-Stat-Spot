import { SuggestionCards } from './SuggestionCards'

export function EnhancedSuggest({ player, result }: { 
  player: { id: number; name: string } | null
  result?: any
}) {
  return (
    <div>
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Analysis Results</h3>
      
      <div className="space-y-4">
        {!player || !player.id ? (
          <div className="text-center py-8 text-gray-500">
            <p className="text-sm">Select a player to view analysis results</p>
          </div>
        ) : result && result.suggestions && result.suggestions.length > 0 ? (
          <SuggestionCards suggestions={result.suggestions || []} />
        ) : result && result.suggestions && result.suggestions.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p className="text-sm">No results found. Please check your market lines and try again.</p>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p className="text-sm">Enter market lines and click "Evaluate" to see analysis results</p>
          </div>
        )}
      </div>

      {/* View Profile Link */}
      {player?.id && (
        <div className="mt-6 pt-4 border-t border-gray-200">
          <a
            href={`/player/${player.id}`}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-700 text-white font-medium rounded-lg hover:bg-blue-800 transition-all shadow-sm border-2 border-blue-800"
            style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 16px', background: '#1d4ed8', color: '#ffffff', borderRadius: '8px', fontWeight: 500, borderColor: '#1e40af' }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ width: '16px', height: '16px', color: '#ffffff' }}>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
            View {player.name}'s Profile
          </a>
        </div>
      )}
    </div>
  )
}
