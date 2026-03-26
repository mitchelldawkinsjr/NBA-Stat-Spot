import { useState, useMemo, useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSeason } from '../context/SeasonContext'
import { apiFetch, apiPost } from '../utils/api'
import type { Bet, BetStats, Parlay, Player, BetResult } from '../types/api'

async function fetchBets(): Promise<Bet[]> {
  const res = await apiFetch('api/v1/bets?limit=100')
  if (!res.ok) throw new Error('Failed to load bets')
  return res.json()
}

async function fetchBetStats(): Promise<BetStats> {
  const res = await apiFetch('api/v1/bets/stats')
  if (!res.ok) throw new Error('Failed to load stats')
  return res.json()
}

async function fetchParlays(): Promise<Parlay[]> {
  const res = await apiFetch('api/v1/parlays?limit=100')
  if (!res.ok) throw new Error('Failed to load parlays')
  const data = await res.json()
  return data.items || []
}

async function searchPlayers(query: string): Promise<Player[]> {
  if (!query || query.length < 1) return []
  const res = await apiFetch(`api/v1/players/search?q=${encodeURIComponent(query)}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.items || []
}

interface PropSuggestionResult {
  confidence?: number
  fairLine?: number
  suggestion?: string
  hitRate?: number
}

async function fetchPropSuggestion(playerId: number, propType: string, lineValue: number, season?: string, lastN?: number, direction?: string): Promise<PropSuggestionResult | null> {
  if (!playerId || !propType || !lineValue) return null
  try {
    const body: {
      playerId: number
      season?: string
      lastN?: number
      marketLines: Record<string, number>
      direction?: string
    } = {
      playerId,
      season: season || '2025-26',
      marketLines: { [propType]: lineValue },
      direction: direction || 'over' // Include direction in request
    }
    // Use lastN=10 as default to match PlayerProfile behavior
    if (lastN !== undefined) {
      body.lastN = lastN
    } else {
      body.lastN = 10 // Default to last 10 games to match PlayerProfile
    }
    
    const data = await apiPost('api/v1/props/player', body)
    if (!data) {
      console.warn('No data returned from API')
      return null
    }
    
    if (data.error) {
      console.error('API returned error:', data.error)
      return null
    }
    
    const suggestion = data.suggestions?.[0]
    if (suggestion) {
      // Use the backend's suggestion directly to match PlayerProfile logic
      // Backend calculates: "over" if hit_rate >= 0.5 else "under"
      // Get hit rate based on direction (over or under) to match PlayerProfile calculation
      const hitRate = direction === 'under' 
        ? (suggestion.hitRateUnder || 0)
        : (suggestion.hitRateOver || suggestion.hitRate || 0)
      
      return {
        confidence: suggestion.confidence,
        fairLine: suggestion.fairLine,
        suggestion: suggestion.suggestion || 'over', // Fallback to 'over' if missing
        hitRate: hitRate // Hit rate as decimal (0.0 to 1.0), matching backend calculation
      }
    } else {
      console.warn('No suggestion found in API response:', data)
    }
  } catch (e) {
    console.error('Failed to fetch prop suggestion:', e)
  }
  return null
}

export function BetTracker() {
  const queryClient = useQueryClient()
  const { season } = useSeason()
  const [showForm, setShowForm] = useState(false)
  const [selectedBet, setSelectedBet] = useState<Bet | null>(null)
  const [betType, setBetType] = useState<'single' | 'parlay'>('single')
  
  const { data: bets = [], isLoading, error: betsError } = useQuery({ queryKey: ['bets'], queryFn: fetchBets })
  const { data: parlays = [], isLoading: parlaysLoading } = useQuery({ queryKey: ['parlays'], queryFn: fetchParlays })
  const { data: stats, error: statsError } = useQuery({ queryKey: ['bet-stats'], queryFn: fetchBetStats })
  
  const handleOpenForm = () => {
    setShowForm(true)
  }
  
  const createBet = useMutation({
    mutationFn: async (betData: {
      player_id: number
      player_name: string
      prop_type: string
      line_value: number
      direction: string
      game_date: string
      system_confidence?: number | null
      system_fair_line?: number | null
      system_suggestion?: string | null
      amount?: number | null
      odds?: string | null
      notes?: string | null
    }) => {
      return await apiPost('api/v1/bets', betData)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bets'] })
      queryClient.invalidateQueries({ queryKey: ['bet-stats'] })
      setShowForm(false)
      setBetType('single')
    }
  })

  const createParlay = useMutation({
    mutationFn: async (parlayData: {
      name?: string | null
      game_date: string
      total_amount?: number | null
      total_odds?: string | null
      notes?: string | null
      legs: Array<{
        player_id: number
        player_name: string
        prop_type: string
        line_value: number
        direction: string
        system_confidence?: number | null
        system_fair_line?: number | null
        system_suggestion?: string | null
        system_hit_rate?: number | null
      }>
    }) => {
      return await apiPost('api/v1/parlays', parlayData)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['parlays'] })
      queryClient.invalidateQueries({ queryKey: ['bet-stats'] })
      setShowForm(false)
      setBetType('single')
    }
  })
  
  const updateBet = useMutation({
    mutationFn: async ({ id, data }: { 
      id: number
      data: {
        result?: string
        actual_value?: number | null
        payout?: number | null
        notes?: string | null
      }
    }) => {
      const res = await apiFetch(`api/v1/bets/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data)
      })
      if (!res.ok) throw new Error('Failed to update bet')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bets'] })
      queryClient.invalidateQueries({ queryKey: ['bet-stats'] })
      setSelectedBet(null)
    }
  })
  
  const pendingBets = useMemo(() => bets.filter(b => b.result === 'pending'), [bets])
  const settledBets = useMemo(() => bets.filter(b => b.result !== 'pending'), [bets])
  
  // Calculate financial totals
  const financialStats = useMemo(() => {
    const settled = bets.filter(b => b.result !== 'pending')
    const totalWagered = settled.reduce((sum, b) => sum + (b.amount || 0), 0)
    const totalPayout = settled.reduce((sum, b) => sum + (b.payout || 0), 0)
    const totalProfit = totalPayout - totalWagered
    const pendingWagered = pendingBets.reduce((sum, b) => sum + (b.amount || 0), 0)
    
    return {
      totalWagered,
      totalPayout,
      totalProfit,
      pendingWagered,
      roi: totalWagered > 0 ? (totalProfit / totalWagered) * 100 : 0
    }
  }, [bets, pendingBets])
  
  return (
    <div className="space-y-3 sm:space-y-4 relative">
      {/* Floating Action Button - Always Visible */}
      <button
        onClick={handleOpenForm}
        type="button"
        className="fixed bottom-24 lg:bottom-8 right-4 sm:right-6 z-40 w-14 h-14 sm:w-16 sm:h-16 bg-primary-container text-on-primary rounded-full shadow-2xl hover:brightness-110 hover:scale-110 transition-all flex items-center justify-center group"
        aria-label="Record new bet"
        title="Record new bet"
        style={{ zIndex: 9999 }}
      >
        <svg className="w-6 h-6 sm:w-7 sm:h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
      </button>
      
      {/* Action Bar - Always Visible at Top */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-surface-container p-4 rounded border border-outline-variant/20">
        <div>
          <h2 className="text-2xl font-black uppercase italic tracking-tighter text-on-surface">PERFORMANCE LEDGER</h2>
          <p className="text-[10px] sm:text-xs text-on-surface-variant mt-0.5 transition-colors duration-200">Track your betting performance</p>
        </div>
        <button
          onClick={handleOpenForm}
          type="button"
          className="px-4 sm:px-6 py-2 sm:py-3 bg-primary-container text-on-primary rounded-lg hover:brightness-110 text-sm sm:text-base font-bold shadow-md hover:shadow-lg transition-all flex items-center gap-2 w-full sm:w-auto sm:min-w-[140px] justify-center"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          <span>Record Bet</span>
        </button>
      </div>
      
      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 sm:gap-4">
          <div className="p-3 sm:p-4 bg-surface-container rounded-lg shadow-sm ring-1 ring-outline-variant/20 transition-colors duration-200">
            <div className="text-[10px] sm:text-xs text-on-surface-variant mb-1 transition-colors duration-200">Overall Win Rate</div>
            <div className="text-xl sm:text-2xl font-bold text-on-surface transition-colors duration-200">{stats.overall.win_rate.toFixed(1)}%</div>
            <div className="text-[10px] sm:text-xs text-on-surface-variant transition-colors duration-200">{stats.overall.won}W / {stats.overall.lost}L / {stats.overall.push}P</div>
          </div>
          <div className="p-3 sm:p-4 bg-surface-container rounded-lg shadow-sm ring-1 ring-outline-variant/20 transition-colors duration-200">
            <div className="text-[10px] sm:text-xs text-on-surface-variant mb-1 transition-colors duration-200">System Accuracy</div>
            <div className="text-xl sm:text-2xl font-bold text-on-surface transition-colors duration-200">{stats.system_accuracy.win_rate.toFixed(1)}%</div>
            <div className="text-[10px] sm:text-xs text-on-surface-variant transition-colors duration-200">{stats.system_accuracy.won}W / {stats.system_accuracy.total} total</div>
          </div>
          <div className="p-3 sm:p-4 bg-surface-container rounded-lg shadow-sm ring-1 ring-outline-variant/20 transition-colors duration-200">
            <div className="text-[10px] sm:text-xs text-on-surface-variant mb-1 transition-colors duration-200">Total Wagered</div>
            <div className="text-xl sm:text-2xl font-bold text-on-surface transition-colors duration-200">${financialStats.totalWagered.toFixed(2)}</div>
            {financialStats.pendingWagered > 0 && (
              <div className="text-[10px] sm:text-xs text-on-surface-variant transition-colors duration-200">${financialStats.pendingWagered.toFixed(2)} pending</div>
            )}
          </div>
          <div className="p-3 sm:p-4 bg-surface-container rounded-lg shadow-sm ring-1 ring-outline-variant/20 col-span-2 sm:col-span-1 transition-colors duration-200">
            <div className="text-[10px] sm:text-xs text-on-surface-variant mb-1 transition-colors duration-200">Total Profit/Loss</div>
            <div className={`text-xl sm:text-2xl font-bold ${financialStats.totalProfit >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'} transition-colors duration-200`}>
              {financialStats.totalProfit >= 0 ? '+' : ''}${financialStats.totalProfit.toFixed(2)}
            </div>
            <div className="text-[10px] sm:text-xs text-on-surface-variant transition-colors duration-200">ROI: {financialStats.roi.toFixed(1)}%</div>
          </div>
          <div className="p-3 sm:p-4 bg-surface-container rounded-lg shadow-sm ring-1 ring-outline-variant/20 transition-colors duration-200">
            <div className="text-[10px] sm:text-xs text-on-surface-variant mb-1 transition-colors duration-200">Pending Bets</div>
            <div className="text-xl sm:text-2xl font-bold text-on-surface transition-colors duration-200">{stats.pending}</div>
          </div>
        </div>
      )}

      {/* Breakdown by Prop Type + Confidence */}
      {stats && stats.overall.total > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
          {/* By Prop Type */}
          {Object.keys(stats.by_prop_type || {}).length > 0 && (
            <div className="bg-surface-container rounded-lg shadow-sm ring-1 ring-outline-variant/20 p-3 sm:p-4 transition-colors duration-200">
              <div className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-3 transition-colors duration-200">Win Rate by Prop Type</div>
              <div className="space-y-2">
                {Object.entries(stats.by_prop_type).map(([type, data]) => {
                  const pct = data.win_rate
                  const barColor = pct >= 60 ? 'bg-betting-green' : pct >= 50 ? 'bg-amber-400' : 'bg-error'
                  return (
                    <div key={type}>
                      <div className="flex justify-between items-center mb-0.5">
                        <span className="text-xs font-medium text-on-surface w-10 transition-colors duration-200">{type}</span>
                        <span className="text-xs text-on-surface-variant transition-colors duration-200">{data.won}W/{data.total}G</span>
                        <span className={`text-xs font-bold w-12 text-right ${pct >= 60 ? 'text-green-600 dark:text-green-400' : pct >= 50 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'} transition-colors duration-200`}>
                          {pct.toFixed(0)}%
                        </span>
                      </div>
                      <div className="w-full bg-surface-container-high rounded-full h-1.5 transition-colors duration-200">
                        <div className={`${barColor} h-1.5 rounded-full transition-all duration-300`} style={{ width: `${Math.min(100, pct)}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* By Confidence */}
          {stats.by_confidence && (
            <div className="bg-surface-container rounded-lg shadow-sm ring-1 ring-outline-variant/20 p-3 sm:p-4 transition-colors duration-200">
              <div className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-3 transition-colors duration-200">System Accuracy by Confidence</div>
              <div className="space-y-2">
                {(['high', 'medium', 'low'] as const).map(level => {
                  const data = stats.by_confidence[level]
                  if (!data || data.total === 0) return null
                  const pct = data.win_rate
                  const labelColor = level === 'high' ? 'text-betting-green' : level === 'medium' ? 'text-amber-400' : 'text-on-surface-variant'
                  const barColor = level === 'high' ? 'bg-betting-green' : level === 'medium' ? 'bg-amber-400' : 'bg-surface-container-highest'
                  const label = level === 'high' ? 'High (≥70%)' : level === 'medium' ? 'Medium (50–69%)' : 'Low (<50%)'
                  return (
                    <div key={level}>
                      <div className="flex justify-between items-center mb-0.5">
                        <span className={`text-xs font-medium transition-colors duration-200 ${labelColor}`}>{label}</span>
                        <span className="text-xs text-on-surface-variant transition-colors duration-200">{data.won}W/{data.total}G</span>
                        <span className={`text-xs font-bold w-12 text-right ${pct >= 60 ? 'text-green-600 dark:text-green-400' : pct >= 50 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'} transition-colors duration-200`}>
                          {pct.toFixed(0)}%
                        </span>
                      </div>
                      <div className="w-full bg-surface-container-high rounded-full h-1.5 transition-colors duration-200">
                        <div className={`${barColor} h-1.5 rounded-full transition-all duration-300`} style={{ width: `${Math.min(100, pct)}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Create Bet Form */}
      {showForm && (
        <BetForm
          betType={betType}
          onBetTypeChange={setBetType}
          onClose={() => {
            setShowForm(false)
            setBetType('single')
          }}
          onSubmit={(data) => {
            if (betType === 'parlay') {
              // Convert ParlayFormData to match API expectations
              const parlayData = data as ParlayFormData
              const convertedData = {
                ...parlayData,
                legs: parlayData.legs.map(leg => ({
                  ...leg,
                  player_id: typeof leg.player_id === 'string' ? Number(leg.player_id) : leg.player_id,
                  line_value: typeof leg.line_value === 'string' ? Number(leg.line_value) : leg.line_value,
                }))
              }
              createParlay.mutate(convertedData)
            } else {
              createBet.mutate(data as BetFormData)
            }
          }}
          isSubmitting={betType === 'parlay' ? createParlay.isPending : createBet.isPending}
          season={season}
        />
      )}
      
      {/* Update Bet Form */}
      {selectedBet && (
        <UpdateBetForm
          bet={selectedBet}
          onClose={() => setSelectedBet(null)}
          onSubmit={(data) => updateBet.mutate({ id: selectedBet.id, data })}
          isSubmitting={updateBet.isPending}
        />
      )}
      
      {/* Pending Bets */}
      {pendingBets.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-on-surface mb-2">Pending ({pendingBets.length})</h3>
          <div className="space-y-2">
            {pendingBets.map(bet => (
              <BetCard key={bet.id} bet={bet} onSelect={() => setSelectedBet(bet)} />
            ))}
          </div>
        </div>
      )}
      
      {/* Settled Bets */}
      {settledBets.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-on-surface mb-2 transition-colors duration-200">Settled ({settledBets.length})</h3>
          <div className="space-y-2">
            {settledBets.map(bet => (
              <BetCard key={bet.id} bet={bet} onSelect={() => setSelectedBet(bet)} />
            ))}
          </div>
        </div>
      )}
      
      {/* Pending Parlays */}
      {parlaysLoading ? (
        <div className="bg-surface-container p-4 rounded-lg shadow-sm ring-1 ring-outline-variant/20 transition-colors duration-200">
          <div className="text-on-surface-variant transition-colors duration-200">Loading parlays...</div>
        </div>
      ) : parlays.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-on-surface mb-2 transition-colors duration-200">Parlays ({parlays.length})</h3>
          <div className="space-y-3">
            {parlays.map((parlay) => (
              <div key={parlay.id} className="p-4 bg-surface-container rounded-lg border border-outline-variant/30 shadow-sm transition-colors duration-200">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h4 className="font-semibold text-on-surface transition-colors duration-200">{parlay.name || `Parlay #${parlay.id}`}</h4>
                    <p className="text-xs text-on-surface-variant mt-0.5 transition-colors duration-200">
                      {new Date(parlay.game_date).toLocaleDateString()} • {parlay.leg_count} legs
                    </p>
                  </div>
                  <div className="text-right">
                    <div className={`text-xs font-semibold px-2 py-1 rounded-full transition-colors duration-200 ${
                      parlay.result === 'won' ? 'bg-betting-green/20 text-betting-green' :
                      parlay.result === 'lost' ? 'bg-error/20 text-error' :
                      parlay.result === 'push' ? 'bg-amber-400/20 text-amber-400' :
                      'bg-surface-container-high text-on-surface-variant'
                    }`}>
                      {parlay.result.toUpperCase()}
                    </div>
                    {parlay.total_amount && (
                      <div className="text-sm font-semibold text-on-surface mt-1 transition-colors duration-200">${parlay.total_amount.toFixed(2)}</div>
                    )}
                  </div>
                </div>
                <div className="space-y-2">
                  {parlay.legs && parlay.legs.map((leg, idx) => (
                    <div key={leg.id || idx} className="p-2 bg-surface-container-high rounded border border-outline-variant/30 transition-colors duration-200">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-on-surface transition-colors duration-200">{leg.player_name}</span>
                            <span className="text-xs px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant border border-outline-variant/30 transition-colors duration-200">{leg.prop_type}</span>
                          </div>
                          <div className="text-xs text-on-surface-variant mt-0.5 transition-colors duration-200">
                            {leg.direction.toUpperCase()} {leg.line_value}
                          </div>
                          {leg.system_confidence !== undefined && leg.system_confidence !== null && (
                            <div className="text-xs text-on-surface-variant mt-1 transition-colors duration-200">
                              System: {leg.system_confidence.toFixed(1)}% confidence ({leg.system_suggestion?.toUpperCase() || 'N/A'})
                              {leg.system_fair_line && (
                                <span className="ml-2">• Fair line: {leg.system_fair_line.toFixed(1)}</span>
                              )}
                              {leg.system_hit_rate !== undefined && leg.system_hit_rate !== null && (
                                <span className="ml-2">• Hit rate: {leg.system_hit_rate.toFixed(0)}%</span>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="text-right">
                          <div className={`text-xs font-semibold px-2 py-0.5 rounded transition-colors duration-200 ${
                            leg.result === 'won' ? 'bg-betting-green/20 text-betting-green' :
                            leg.result === 'lost' ? 'bg-error/20 text-error' :
                            leg.result === 'push' ? 'bg-amber-400/20 text-amber-400' :
                            'bg-surface-container text-on-surface-variant'
                          }`}>
                            {leg.result.toUpperCase()}
                          </div>
                          {leg.actual_value !== undefined && leg.actual_value !== null && (
                            <div className="text-xs text-on-surface-variant mt-0.5 transition-colors duration-200">Actual: {leg.actual_value.toFixed(1)}</div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                {parlay.system_confidence && (
                  <div className="mt-3 pt-3 border-t border-outline-variant/30 text-xs text-on-surface-variant transition-colors duration-200">
                    <span className="font-medium">Avg System Confidence:</span> {parlay.system_confidence.toFixed(1)}%
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Error Messages */}
      {(betsError || statsError) && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
          <p className="font-semibold">Error loading data</p>
          <p className="text-xs mt-1">You can still record bets using the button above.</p>
        </div>
      )}
      
      {isLoading && (
        <div className="bg-surface-container p-4 rounded-lg shadow-sm ring-1 ring-outline-variant/20 transition-colors duration-200">
          <div className="text-on-surface-variant">Loading bets...</div>
        </div>
      )}
      {!isLoading && bets.length === 0 && !betsError && (
        <div className="text-center py-12">
          <div className="max-w-md mx-auto">
            <div className="mb-4">
              <svg className="mx-auto h-16 w-16 text-on-surface-variant/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-on-surface mb-2 transition-colors duration-200">No bets tracked yet</h3>
            <p className="text-sm text-on-surface-variant mb-6 transition-colors duration-200">
              Start tracking your bets to see your performance and system accuracy over time.
            </p>
            <button
              onClick={handleOpenForm}
              type="button"
              className="px-6 py-3 bg-primary-container text-on-primary rounded-lg hover:brightness-110 font-medium shadow-sm"
            >
              Record Your First Bet
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function BetCard({ bet, onSelect }: { bet: Bet; onSelect: () => void }) {
  const resultColor = {
    won: 'bg-betting-green/10 text-betting-green ring-betting-green/30',
    lost: 'bg-error/10 text-error ring-error/30',
    push: 'bg-amber-400/10 text-amber-400 ring-amber-400/30',
    pending: 'bg-surface-container-high text-on-surface-variant ring-outline-variant/30',
    void: 'bg-surface-container-high text-on-surface-variant ring-outline-variant/30'
  }[bet.result] || 'bg-surface-container-high text-on-surface-variant ring-outline-variant/30'
  
  return (
    <div
      className={`p-3 rounded-lg border cursor-pointer hover:shadow-md transition-shadow ${resultColor.split(' ')[0]} border-${resultColor.split(' ')[1].replace('ring-', '')}`}
      onClick={onSelect}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-on-surface transition-colors duration-200">{bet.player_name}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface font-medium border border-outline-variant/30 transition-colors duration-200">{bet.prop_type}</span>
          </div>
          <div className="text-sm text-on-surface-variant mt-1 transition-colors duration-200">
            {bet.direction.toUpperCase()} {bet.line_value} • {new Date(bet.game_date).toLocaleDateString()}
          </div>
          {bet.system_confidence && (
            <div className="text-xs text-on-surface-variant mt-1 transition-colors duration-200">
              System: {bet.system_confidence.toFixed(0)}% confidence ({bet.system_suggestion?.toUpperCase()})
            </div>
          )}
          {bet.result === 'pending' && bet.actual_value !== null && bet.actual_value !== undefined && (
            <div className="text-xs text-on-surface-variant mt-1 transition-colors duration-200">
              Actual: {bet.actual_value.toFixed(1)}
            </div>
          )}
        </div>
        <div className="text-right">
          <div className={`text-xs font-semibold px-2 py-1 rounded-full ${resultColor}`}>
            {bet.result.toUpperCase()}
          </div>
          {bet.amount && (
            <div className="text-sm font-semibold text-on-surface mt-1 transition-colors duration-200">${bet.amount.toFixed(2)}</div>
          )}
          {bet.odds && (
            <div className="text-xs text-on-surface-variant mt-0.5 transition-colors duration-200">{bet.odds}</div>
          )}
          {bet.amount && bet.odds && bet.result === 'won' && bet.payout && (
            <div className="text-xs text-betting-green font-medium mt-0.5 transition-colors duration-200">+${(bet.payout - bet.amount).toFixed(2)}</div>
          )}
        </div>
      </div>
    </div>
  )
}

interface BetFormData {
  player_id: number
  player_name: string
  prop_type: string
  line_value: number
  direction: string
  game_date: string
  system_confidence?: number | null
  system_fair_line?: number | null
  system_suggestion?: string | null
  amount?: number | null
  odds?: string | null
  notes?: string | null
}

interface ParlayFormData {
  name?: string | null
  game_date: string
  total_amount?: number | null
  total_odds?: string | null
  notes?: string | null
  legs: Array<{
    player_id: number | string
    player_name: string
    prop_type: string
    line_value: number | string
    direction: string
    system_confidence?: number | null
    system_fair_line?: number | null
    system_suggestion?: string | null
    system_hit_rate?: number | null
  }>
}

function BetForm({ betType, onBetTypeChange, onClose, onSubmit, isSubmitting, season }: { 
  betType: 'single' | 'parlay'
  onBetTypeChange: (type: 'single' | 'parlay') => void
  onClose: () => void
  onSubmit: (data: BetFormData | ParlayFormData) => void
  isSubmitting: boolean
  season?: string
}) {
  // Single bet form state
  const [formData, setFormData] = useState({
    player_id: '',
    player_name: '',
    prop_type: 'PTS',
    line_value: '',
    direction: 'over',
    game_date: new Date().toISOString().split('T')[0],
    system_confidence: '',
    system_fair_line: '',
    system_suggestion: '',
    amount: '',
    odds: '',
    notes: ''
  })

  // Parlay form state
  const [parlayData, setParlayData] = useState({
    name: '',
    game_date: new Date().toISOString().split('T')[0],
    total_amount: '',
    total_odds: '',
    notes: '',
    legs: [] as Array<{
      player_id: string
      player_name: string
      prop_type: string
      line_value: string
      direction: string
      system_confidence?: number
      system_fair_line?: number
      system_suggestion?: string
      system_hit_rate?: number  // Hit rate as percentage (0-100) to match PlayerProfile
    }>
  })

  // Autocomplete state
  const [playerSearchQuery, setPlayerSearchQuery] = useState('')
  const [playerSuggestions, setPlayerSuggestions] = useState<Array<{id: number; name: string}>>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  // Parlay leg autocomplete state (per leg)
  const [parlayLegSuggestions, setParlayLegSuggestions] = useState<Record<number, Array<{id: number; name: string}>>>({})
  const [parlayLegShowSuggestions, setParlayLegShowSuggestions] = useState<Record<number, boolean>>({})
  const [parlayLegSearchQuery, setParlayLegSearchQuery] = useState<Record<number, string>>({})
  const parlayLegSearchTimeoutRef = useRef<Record<number, ReturnType<typeof setTimeout>>>({})
  // Track which leg is being evaluated
  const [evaluatingLegIndex, setEvaluatingLegIndex] = useState<number | null>(null)

  // Debounced player search
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }
    
    if (playerSearchQuery.length >= 2) {
      searchTimeoutRef.current = setTimeout(async () => {
        setIsSearching(true)
        const results = await searchPlayers(playerSearchQuery)
        setPlayerSuggestions(results)
        setShowSuggestions(true)
        setIsSearching(false)
      }, 300)
    } else {
      setPlayerSuggestions([])
      setShowSuggestions(false)
    }

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [playerSearchQuery])

  // Auto-fetch confidence when player_id, prop_type, and line_value are available
  useEffect(() => {
    if (betType === 'single' && formData.player_id && formData.prop_type && formData.line_value) {
      const playerId = Number(formData.player_id)
      const lineValue = Number(formData.line_value)
      if (playerId && lineValue) {
        fetchPropSuggestion(playerId, formData.prop_type, lineValue, season, undefined, formData.direction).then(suggestion => {
          if (suggestion) {
            setFormData(prev => ({
              ...prev,
              system_confidence: suggestion.confidence?.toString() || prev.system_confidence,
              system_fair_line: suggestion.fairLine?.toString() || prev.system_fair_line,
              system_suggestion: suggestion.suggestion || prev.system_suggestion,
              // Store hit rate if available (as percentage to match PlayerProfile display)
              system_hit_rate: suggestion.hitRate ? Math.round(suggestion.hitRate * 100) : undefined
            }))
          }
        })
      }
    }
  }, [formData.player_id, formData.prop_type, formData.line_value, formData.direction, betType, season])
  
  // Calculate potential payout from amount and odds
  const calculatePayout = (amount: string, odds: string): number | null => {
    if (!amount || !odds) return null
    const betAmount = Number(amount)
    const oddsNum = Number(odds)
    if (isNaN(betAmount) || isNaN(oddsNum) || betAmount <= 0) return null
    
    if (oddsNum > 0) {
      // Positive odds (e.g., +150): win = bet * (odds/100)
      return betAmount + (betAmount * (oddsNum / 100))
    } else {
      // Negative odds (e.g., -110): win = bet + (bet * (100/abs(odds)))
      return betAmount + (betAmount * (100 / Math.abs(oddsNum)))
    }
  }
  
  const potentialPayout = calculatePayout(formData.amount, formData.odds)
  const potentialProfit = potentialPayout ? potentialPayout - Number(formData.amount || 0) : null
  
  // Handle player selection from autocomplete
  const handlePlayerSelect = (player: {id: number; name: string}) => {
    if (betType === 'single') {
      setFormData(prev => ({
        ...prev,
        player_id: player.id.toString(),
        player_name: player.name
      }))
    }
    setPlayerSearchQuery(player.name)
    setShowSuggestions(false)
  }

  // Add parlay leg
  const addParlayLeg = () => {
    setParlayData(prev => ({
      ...prev,
      legs: [...prev.legs, {
        player_id: '',
        player_name: '',
        prop_type: 'PTS',
        line_value: '',
        direction: 'over'
      }]
    }))
  }

  // Remove parlay leg
  const removeParlayLeg = (index: number) => {
    setParlayData(prev => ({
      ...prev,
      legs: prev.legs.filter((_, i) => i !== index)
    }))
  }

  // Manually evaluate a parlay leg
  const evaluateParlayLeg = async (index: number) => {
    const leg = parlayData.legs[index]
    if (!leg || !leg.player_id || !leg.prop_type || !leg.line_value) {
      alert('Please fill in Player ID, Prop Type, and Line Value before evaluating')
      return
    }
    
    setEvaluatingLegIndex(index)
    try {
      const playerId = Number(leg.player_id)
      const lineValue = Number(leg.line_value)
      if (playerId && lineValue) {
        const suggestion = await fetchPropSuggestion(playerId, leg.prop_type, lineValue, season, undefined, leg.direction)
        if (suggestion && (suggestion.confidence !== undefined || suggestion.fairLine !== undefined)) {
          setParlayData(prevData => ({
            ...prevData,
            legs: prevData.legs.map((l, i) => 
              i === index ? {
                ...l,
                system_confidence: suggestion.confidence,
                system_fair_line: suggestion.fairLine,
                system_suggestion: suggestion.suggestion,
                // Store hit rate if available (as percentage to match PlayerProfile display)
                system_hit_rate: suggestion.hitRate ? Math.round(suggestion.hitRate * 100) : undefined
              } : l
            )
          }))
        } else {
          alert('No evaluation results found. Please check that the player ID, prop type, and line value are correct.')
        }
      } else {
        alert('Invalid player ID or line value. Please check your inputs.')
      }
    } catch (error) {
      console.error('Failed to evaluate parlay leg:', error)
      alert('Failed to evaluate leg. Please check your inputs and try again.')
    } finally {
      setEvaluatingLegIndex(null)
    }
  }

  // Update parlay leg
  const updateParlayLeg = (index: number, field: string, value: string | number) => {
    setParlayData(prev => {
      const updatedLegs = prev.legs.map((leg, i) => 
        i === index ? { ...leg, [field]: value } : leg
      )
      
      // Auto-fetch confidence for parlay leg when player_id, prop_type, and line_value are all set
      if ((field === 'player_id' || field === 'prop_type' || field === 'line_value' || field === 'direction') && index !== undefined) {
        const updatedLeg = updatedLegs[index]
        if (updatedLeg.player_id && updatedLeg.prop_type && updatedLeg.line_value) {
          const playerId = Number(updatedLeg.player_id)
          const lineValue = Number(updatedLeg.line_value)
          if (playerId && lineValue) {
            fetchPropSuggestion(playerId, updatedLeg.prop_type, lineValue, season, undefined, updatedLeg.direction).then(suggestion => {
              if (suggestion) {
                setParlayData(prevData => ({
                  ...prevData,
                  legs: prevData.legs.map((l, i) => 
                    i === index ? {
                      ...l,
                      system_confidence: suggestion.confidence,
                      system_fair_line: suggestion.fairLine,
                      system_suggestion: suggestion.suggestion,
                      // Store hit rate if available (as percentage to match PlayerProfile display)
                      system_hit_rate: suggestion.hitRate ? Math.round(suggestion.hitRate * 100) : undefined
                    } : l
                  )
                }))
              }
            })
          }
        }
      }

      return {
        ...prev,
        legs: updatedLegs
      }
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (betType === 'parlay') {
      if (parlayData.legs.length < 2) {
        alert('Parlay must have at least 2 legs')
        return
      }
      onSubmit({
        name: parlayData.name || null,
        game_date: parlayData.game_date,
        total_amount: parlayData.total_amount ? Number(parlayData.total_amount) : null,
        total_odds: parlayData.total_odds || null,
        notes: parlayData.notes || null,
        legs: parlayData.legs.map(leg => ({
          player_id: Number(leg.player_id),
          player_name: leg.player_name,
          prop_type: leg.prop_type,
          line_value: Number(leg.line_value),
          direction: leg.direction,
          system_confidence: leg.system_confidence || null,
          system_fair_line: leg.system_fair_line || null,
          system_suggestion: leg.system_suggestion || null,
          system_hit_rate: leg.system_hit_rate || null
        }))
      })
    } else {
      onSubmit({
        ...formData,
        player_id: Number(formData.player_id),
        line_value: Number(formData.line_value),
        system_confidence: formData.system_confidence ? Number(formData.system_confidence) : null,
        system_fair_line: formData.system_fair_line ? Number(formData.system_fair_line) : null,
        amount: formData.amount ? Number(formData.amount) : null
      })
    }
  }

  const parlayPotentialPayout = calculatePayout(parlayData.total_amount, parlayData.total_odds)
  const parlayPotentialProfit = parlayPotentialPayout ? parlayPotentialPayout - Number(parlayData.total_amount || 0) : null
  const parlaySystemConfidence = parlayData.legs.length > 0 
    ? parlayData.legs.reduce((sum, leg) => sum + (leg.system_confidence || 0), 0) / parlayData.legs.length
    : 0
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100] p-4" onClick={onClose}>
      <div className="bg-surface-container rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto relative transition-colors duration-200" onClick={(e) => e.stopPropagation()}>
        <div className="p-4 border-b border-outline-variant/30 flex items-center justify-between sticky top-0 bg-surface-container z-10 transition-colors duration-200">
          <h3 className="text-lg font-semibold text-on-surface transition-colors duration-200">
            {betType === 'parlay' ? 'Record New Parlay' : 'Record New Bet'}
          </h3>
          <button 
            onClick={onClose} 
            className="text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high rounded-full p-1 transition-colors"
            type="button"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Bet Type Toggle */}
        <div className="p-4 border-b border-outline-variant/30 transition-colors duration-200">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => onBetTypeChange('single')}
              className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                betType === 'single'
                  ? 'bg-primary-container text-on-primary'
                  : 'bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest'
              }`}
            >
              Single Bet
            </button>
            <button
              type="button"
              onClick={() => onBetTypeChange('parlay')}
              className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                betType === 'parlay'
                  ? 'bg-primary-container text-on-primary'
                  : 'bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest'
              }`}
            >
              Parlay
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-3">
          {betType === 'single' ? (
            <>
              {/* Player Name with Autocomplete */}
              <div className="relative">
                <label className="block text-xs font-medium text-on-surface-variant mb-1 transition-colors duration-200">Player Name *</label>
                <input
                  type="text"
                  value={playerSearchQuery || formData.player_name}
                  onChange={(e) => {
                    setPlayerSearchQuery(e.target.value)
                    setFormData(prev => ({ ...prev, player_name: e.target.value }))
                  }}
                  onFocus={() => {
                    if (playerSearchQuery.length >= 2) setShowSuggestions(true)
                  }}
                  required
                  className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high focus:outline-none focus:ring-2 focus:ring-secondary-container/25 transition-colors duration-200"
                  placeholder="Search for player..."
                />
                {showSuggestions && playerSuggestions.length > 0 && (
                  <div className="absolute z-[150] w-full mt-1 bg-surface-container border border-outline/30 rounded-lg shadow-lg max-h-60 overflow-y-auto transition-colors duration-200">
                    {isSearching && (
                      <div className="px-3 py-2 text-sm text-on-surface-variant">Searching...</div>
                    )}
                    {playerSuggestions.map((player) => (
                      <button
                        key={player.id}
                        type="button"
                        onClick={() => handlePlayerSelect(player)}
                        className="w-full text-left px-3 py-2 hover:bg-surface-container-high text-sm text-on-surface transition-colors"
                      >
                        {player.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Player ID (auto-filled) */}
              <div>
                <label className="block text-xs font-medium text-on-surface-variant mb-1 transition-colors duration-200">Player ID *</label>
                <input
                  type="number"
                  value={formData.player_id}
                  onChange={(e) => setFormData({ ...formData, player_id: e.target.value })}
                  required
                  className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm bg-surface-container-high text-on-surface transition-colors duration-200"
                  readOnly={!!formData.player_id}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-on-surface-variant mb-1 transition-colors duration-200">Prop Type</label>
              <select
                value={formData.prop_type}
                onChange={(e) => setFormData({ ...formData, prop_type: e.target.value })}
                className="w-full px-3 pr-10 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high transition-colors duration-200"
              >
                <option className="text-on-surface bg-surface-container-high">PTS</option>
                <option className="text-on-surface bg-surface-container-high">REB</option>
                <option className="text-on-surface bg-surface-container-high">AST</option>
                <option className="text-on-surface bg-surface-container-high">3PM</option>
                <option className="text-on-surface bg-surface-container-high">PRA</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-on-surface-variant mb-1 transition-colors duration-200">Direction</label>
              <select
                value={formData.direction}
                onChange={(e) => setFormData({ ...formData, direction: e.target.value })}
                className="w-full px-3 pr-10 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high transition-colors duration-200"
              >
                <option className="text-on-surface bg-surface-container-high">over</option>
                <option className="text-on-surface bg-surface-container-high">under</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-on-surface-variant mb-1">Line Value</label>
              <input
                type="number"
                step="0.5"
                value={formData.line_value}
                onChange={(e) => setFormData({ ...formData, line_value: e.target.value })}
                required
                className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-on-surface-variant mb-1">Game Date</label>
              <input
                type="date"
                value={formData.game_date}
                onChange={(e) => setFormData({ ...formData, game_date: e.target.value })}
                required
                className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
              />
            </div>
          </div>
          
          {/* Betting Amount & Odds Section - More Prominent */}
          <div className="border-t border-outline-variant/30 pt-4 mt-4">
            <div className="text-xs font-semibold text-on-surface-variant mb-2">Betting Details</div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-on-surface-variant mb-1">Wager Amount ($) *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                  className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high focus:ring-2 focus:ring-secondary-container/25 focus:outline-none"
                  placeholder="100.00"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-on-surface-variant mb-1">Odds *</label>
                <input
                  type="text"
                  placeholder="-110 or +150"
                  value={formData.odds}
                  onChange={(e) => setFormData({ ...formData, odds: e.target.value })}
                  className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high focus:ring-2 focus:ring-secondary-container/25 focus:outline-none"
                />
                <div className="text-xs text-on-surface-variant mt-1">American format</div>
              </div>
            </div>
            {potentialPayout && potentialProfit !== null && (
              <div className="mt-3 p-2 bg-surface-container-high rounded-lg border border-outline/30">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-on-surface-variant">Potential Payout:</span>
                  <span className="font-semibold text-on-surface">${potentialPayout.toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between text-xs mt-1">
                  <span className="text-on-surface-variant">Potential Profit:</span>
                  <span className={`font-medium ${potentialProfit >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                    {potentialProfit >= 0 ? '+' : ''}${potentialProfit.toFixed(2)}
                  </span>
                </div>
              </div>
            )}
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-on-surface-variant mb-1">System Confidence (%)</label>
              <input
                type="number"
                step="0.1"
                value={formData.system_confidence}
                onChange={(e) => setFormData({ ...formData, system_confidence: e.target.value })}
                className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-on-surface-variant mb-1">System Suggestion</label>
              <select
                value={formData.system_suggestion}
                onChange={(e) => setFormData({ ...formData, system_suggestion: e.target.value })}
                className="w-full px-3 pr-10 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
              >
                <option value="" className="text-on-surface">N/A</option>
                <option className="text-on-surface">over</option>
                <option className="text-on-surface">under</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-on-surface-variant mb-1">Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
            />
          </div>
          <div className="flex gap-3 pt-4 border-t border-outline-variant/30">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-outline/30 rounded-lg text-sm font-medium text-on-surface-variant hover:bg-surface-container-high transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-primary-container text-on-primary rounded-lg text-sm font-medium hover:brightness-110 disabled:opacity-50 transition-colors"
            >
              {isSubmitting ? 'Saving...' : 'Save Bet'}
            </button>
          </div>
            </>
          ) : (
            <>
              {/* Parlay Form */}
              <div>
                <label className="block text-xs font-medium text-on-surface-variant mb-1">Parlay Name (Optional)</label>
                <input
                  type="text"
                  value={parlayData.name}
                  onChange={(e) => setParlayData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
                  placeholder="e.g., Saturday Night Parlay"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-on-surface-variant mb-1">Game Date *</label>
                <input
                  type="date"
                  value={parlayData.game_date}
                  onChange={(e) => setParlayData(prev => ({ ...prev, game_date: e.target.value }))}
                  required
                  className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
                />
              </div>

              {/* Parlay Legs */}
              <div className="border-t border-outline-variant/30 pt-4">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <div className="text-sm font-semibold text-on-surface">Parlay Legs</div>
                    <div className="text-xs text-on-surface-variant">Minimum 2 legs required</div>
                  </div>
                  <button
                    type="button"
                    onClick={addParlayLeg}
                    className="px-4 py-2 text-sm bg-primary-container text-on-primary rounded-lg hover:brightness-110 transition-colors font-medium shadow-sm"
                  >
                    + Add Leg
                  </button>
                </div>

                {parlayData.legs.map((leg, index) => (
                  <div key={index} className="mb-4 p-4 border border-outline-variant/30 rounded-lg space-y-3 bg-surface-container-high">
                    <div className="flex items-center justify-between mb-2 pb-2 border-b border-outline-variant/30">
                      <span className="text-sm font-semibold text-on-surface">Leg {index + 1}</span>
                      <button
                        type="button"
                        onClick={() => removeParlayLeg(index)}
                        className="text-xs px-2 py-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors"
                      >
                        Remove
                      </button>
                    </div>

                    <div className="relative">
                      <label className="block text-xs font-medium text-on-surface-variant mb-1">Player Name *</label>
                      <input
                        type="text"
                        value={parlayLegSearchQuery[index] !== undefined ? parlayLegSearchQuery[index] : leg.player_name}
                        onChange={(e) => {
                          const query = e.target.value
                          setParlayLegSearchQuery(prev => ({ ...prev, [index]: query }))
                          updateParlayLeg(index, 'player_name', query)
                          
                          // Debounced search
                          if (parlayLegSearchTimeoutRef.current[index]) {
                            clearTimeout(parlayLegSearchTimeoutRef.current[index])
                          }
                          
                          if (query.length >= 2) {
                            parlayLegSearchTimeoutRef.current[index] = setTimeout(async () => {
                              const results = await searchPlayers(query)
                              setParlayLegSuggestions(prev => ({ ...prev, [index]: results }))
                              setParlayLegShowSuggestions(prev => ({ ...prev, [index]: true }))
                            }, 300)
                          } else {
                            setParlayLegSuggestions(prev => {
                              const updated = { ...prev }
                              delete updated[index]
                              return updated
                            })
                            setParlayLegShowSuggestions(prev => ({ ...prev, [index]: false }))
                          }
                        }}
                        onFocus={() => {
                          if (parlayLegSearchQuery[index] && parlayLegSearchQuery[index].length >= 2) {
                            setParlayLegShowSuggestions(prev => ({ ...prev, [index]: true }))
                          }
                        }}
                        onBlur={() => {
                          // Delay hiding to allow click
                          setTimeout(() => {
                            setParlayLegShowSuggestions(prev => ({ ...prev, [index]: false }))
                          }, 200)
                        }}
                        required
                        className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container"
                        placeholder="Search player..."
                      />
                      {parlayLegShowSuggestions[index] && parlayLegSuggestions[index] && parlayLegSuggestions[index].length > 0 && (
                        <div className="absolute z-[150] w-full mt-1 bg-surface-container border border-outline-variant/30 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                          {parlayLegSuggestions[index].map((player) => (
                            <button
                              key={player.id}
                              type="button"
                              onMouseDown={(e) => {
                                e.preventDefault()
                                updateParlayLeg(index, 'player_id', player.id.toString())
                                updateParlayLeg(index, 'player_name', player.name)
                                setParlayLegSearchQuery(prev => ({ ...prev, [index]: player.name }))
                                setParlayLegShowSuggestions(prev => ({ ...prev, [index]: false }))
                              }}
                              className="w-full text-left px-3 py-2 hover:bg-surface-container-high text-sm text-on-surface transition-colors"
                            >
                              {player.name}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-on-surface-variant mb-1">Player ID *</label>
                      <input
                        type="number"
                        value={leg.player_id}
                        onChange={(e) => updateParlayLeg(index, 'player_id', e.target.value)}
                        required
                        className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm bg-surface-container text-on-surface-variant"
                        readOnly={!!leg.player_id}
                      />
                    </div>

                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="block text-xs font-medium text-on-surface-variant mb-1">Prop Type</label>
                        <select
                          value={leg.prop_type}
                          onChange={(e) => updateParlayLeg(index, 'prop_type', e.target.value)}
                          className="w-full px-2 pr-8 py-1 border border-outline/30 rounded text-xs text-on-surface bg-surface-container"
                        >
                          <option className="text-on-surface">PTS</option>
                          <option className="text-on-surface">REB</option>
                          <option className="text-on-surface">AST</option>
                          <option className="text-on-surface">3PM</option>
                          <option className="text-on-surface">PRA</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-on-surface-variant mb-1">Line Value</label>
                        <input
                          type="number"
                          step="0.5"
                          value={leg.line_value}
                          onChange={(e) => updateParlayLeg(index, 'line_value', e.target.value)}
                          required
                          className="w-full px-2 py-1 border border-outline/30 rounded text-xs text-on-surface bg-surface-container"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-on-surface-variant mb-1">Direction</label>
                        <select
                          value={leg.direction}
                          onChange={(e) => updateParlayLeg(index, 'direction', e.target.value)}
                          className="w-full px-2 pr-8 py-1 border border-outline/30 rounded text-xs text-on-surface bg-surface-container"
                        >
                          <option className="text-on-surface">over</option>
                          <option className="text-on-surface">under</option>
                        </select>
                      </div>
                    </div>

                    {/* Elevate Button - Prominent placement after form fields */}
                    <div className="pt-2 border-t border-outline-variant/30">
                      <button
                        type="button"
                        onClick={() => evaluateParlayLeg(index)}
                        disabled={!leg.player_id || !leg.prop_type || !leg.line_value || evaluatingLegIndex === index}
                        className={`w-full px-4 py-3 text-sm font-semibold rounded-lg transition-all shadow-md ${
                          evaluatingLegIndex === index
                            ? 'bg-primary-container/60 text-on-primary cursor-wait'
                            : !leg.player_id || !leg.prop_type || !leg.line_value
                            ? 'bg-surface-container text-on-surface-variant/50 cursor-not-allowed'
                            : 'bg-primary-container text-on-primary hover:brightness-110 hover:shadow-lg active:scale-95'
                        }`}
                      >
                        {evaluatingLegIndex === index ? (
                          <span className="flex items-center justify-center gap-2">
                            <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Evaluating...
                          </span>
                        ) : (
                          <span className="flex items-center justify-center gap-2">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            Evaluate Prop
                          </span>
                        )}
                      </button>
                      {(!leg.player_id || !leg.prop_type || !leg.line_value) && (
                        <p className="text-xs text-on-surface-variant mt-2 text-center">
                          Fill in Player ID, Prop Type, and Line Value to evaluate
                        </p>
                      )}
                    </div>

                    {leg.system_confidence !== undefined && (
                      <div className="text-xs text-on-surface-variant mt-2 p-3 bg-surface-container rounded-lg border border-outline-variant/30 shadow-sm">
                        <div className="font-semibold text-on-surface mb-1">System Analysis</div>
                        <div className="space-y-1">
                          <div><span className="font-medium">Confidence:</span> {leg.system_confidence.toFixed(1)}% ({leg.system_suggestion?.toUpperCase()})</div>
                        {leg.system_fair_line && (
                            <div><span className="font-medium">Fair Line:</span> {leg.system_fair_line.toFixed(1)}</div>
                        )}
                        {leg.system_hit_rate !== undefined && (
                            <div><span className="font-medium">Hit Rate:</span> {leg.system_hit_rate}%</div>
                        )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {parlayData.legs.length === 0 && (
                  <div className="text-center py-6 text-sm text-on-surface-variant border-2 border-dashed border-outline-variant/30 rounded-lg">
                    <p className="mb-2">No legs added yet</p>
                    <p className="text-xs">Click "Add Leg" above to add your first parlay leg</p>
                  </div>
                )}
              </div>

              {/* Parlay Betting Details */}
              <div className="border-t border-outline-variant/30 pt-4 mt-4">
                <div className="text-sm font-semibold text-on-surface mb-3">Parlay Betting Details</div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-on-surface-variant mb-1">Total Wager ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={parlayData.total_amount}
                      onChange={(e) => setParlayData(prev => ({ ...prev, total_amount: e.target.value }))}
                      className="w-full px-3 py-2 border-2 border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
                      placeholder="100.00"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-on-surface-variant mb-1">Total Odds</label>
                    <input
                      type="text"
                      placeholder="+450"
                      value={parlayData.total_odds}
                      onChange={(e) => setParlayData(prev => ({ ...prev, total_odds: e.target.value }))}
                      className="w-full px-3 py-2 border-2 border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
                    />
                  </div>
                </div>

                {parlayPotentialPayout && parlayPotentialProfit !== null && (
                  <div className="mt-4 p-3 bg-surface-container rounded-lg border border-outline-variant/30">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-on-surface-variant">Potential Payout:</span>
                      <span className="font-semibold text-on-surface">${parlayPotentialPayout.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center justify-between text-xs mt-1">
                      <span className="text-on-surface-variant">Potential Profit:</span>
                      <span className={`font-medium ${parlayPotentialProfit >= 0 ? 'text-betting-green' : 'text-error'}`}>
                        {parlayPotentialProfit >= 0 ? '+' : ''}${parlayPotentialProfit.toFixed(2)}
                      </span>
                    </div>
                    {parlaySystemConfidence > 0 && (
                      <div className="flex items-center justify-between text-xs mt-1">
                        <span className="text-on-surface-variant">Avg System Confidence:</span>
                        <span className="font-medium text-on-surface">{parlaySystemConfidence.toFixed(1)}%</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-on-surface-variant mb-1">Notes</label>
                <textarea
                  value={parlayData.notes}
                  onChange={(e) => setParlayData(prev => ({ ...prev, notes: e.target.value }))}
                  rows={2}
                  className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
                />
              </div>

              <div className="flex gap-3 pt-4 border-t border-outline-variant/30">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 px-4 py-2 border border-outline/30 rounded-lg text-sm font-medium text-on-surface-variant hover:bg-surface-container-high"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || parlayData.legs.length < 2}
                  className="flex-1 px-4 py-2 bg-primary-container text-on-primary rounded-lg text-sm font-medium hover:brightness-110 disabled:opacity-50"
                >
                  {isSubmitting ? 'Saving...' : 'Save Parlay'}
                </button>
              </div>
            </>
          )}
        </form>
      </div>
    </div>
  )
}

function UpdateBetForm({ bet, onClose, onSubmit, isSubmitting }: { 
  bet: Bet
  onClose: () => void
  onSubmit: (data: {
    result: BetResult
    actual_value?: number | null
    payout?: number | null
    notes?: string | null
  }) => void
  isSubmitting: boolean 
}) {
  const [formData, setFormData] = useState({
    result: bet.result,
    actual_value: bet.actual_value?.toString() || '',
    payout: bet.payout?.toString() || '',
    notes: bet.notes || ''
  })
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      result: formData.result as BetResult,
      actual_value: formData.actual_value ? Number(formData.actual_value) : null,
      payout: formData.payout ? Number(formData.payout) : null,
      notes: formData.notes || null
    })
  }
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100] p-4" onClick={onClose}>
      <div className="bg-surface-container rounded-lg shadow-xl max-w-md w-full" onClick={(e) => e.stopPropagation()}>
        <div className="p-4 border-b border-outline-variant/30 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-on-surface">Update Bet</h3>
          <button onClick={onClose} className="text-on-surface-variant hover:text-on-surface">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-3">
          <div>
            <div className="text-sm font-medium text-on-surface mb-2">{bet.player_name} - {bet.prop_type} {bet.direction.toUpperCase()} {bet.line_value}</div>
          </div>
          <div>
            <label className="block text-xs font-medium text-on-surface-variant mb-1">Result</label>
            <select
              value={formData.result}
              onChange={(e) => setFormData({ ...formData, result: e.target.value as BetResult })}
              className="w-full px-3 pr-10 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
            >
              <option value="pending" className="text-on-surface">Pending</option>
              <option value="won" className="text-on-surface">Won</option>
              <option value="lost" className="text-on-surface">Lost</option>
              <option value="push" className="text-on-surface">Push</option>
              <option value="void" className="text-on-surface">Void</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-on-surface-variant mb-1">Actual Value</label>
            <input
              type="number"
              step="0.1"
              value={formData.actual_value}
              onChange={(e) => setFormData({ ...formData, actual_value: e.target.value })}
              className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-on-surface-variant mb-1">Payout ($)</label>
            <input
              type="number"
              step="0.01"
              value={formData.payout}
              onChange={(e) => setFormData({ ...formData, payout: e.target.value })}
              className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-on-surface-variant mb-1">Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-outline/30 rounded-lg text-sm text-on-surface bg-surface-container-high"
            />
          </div>
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-outline/30 rounded-lg text-sm font-medium text-on-surface-variant hover:bg-surface-container-high"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-primary-container text-on-primary rounded-lg text-sm font-medium hover:brightness-110 disabled:opacity-50"
            >
              {isSubmitting ? 'Updating...' : 'Update Bet'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

