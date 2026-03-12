import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiPost } from '../utils/api'
import { useSnackbar } from '../context/SnackbarContext'

export type AddPropPayload = {
  player_id: number
  player_name: string
  prop_type: string
  line_value: number
  direction: string
  game_date?: string
  system_confidence?: number | null
  system_fair_line?: number | null
  system_suggestion?: string | null
}

export function useAddPropToTracker() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { showSnackbar } = useSnackbar()

  const mutation = useMutation({
    mutationFn: async (payload: AddPropPayload) => {
      const game_date = payload.game_date ?? new Date().toISOString().split('T')[0]
      return apiPost('api/v1/bets', {
        ...payload,
        game_date,
        amount: null,
        odds: '-110',
        notes: null,
      })
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['bets'] })
      queryClient.invalidateQueries({ queryKey: ['bet-stats'] })
      const label = `${variables.player_name} — ${variables.prop_type} ${variables.direction.toUpperCase()} ${variables.line_value}`
      showSnackbar(`Added to Bet Tracker: ${label}`, 'success', {
        duration: 5000,
        action: {
          label: 'View Bet Tracker',
          onClick: () => navigate('/bets'),
        },
      })
    },
    onError: (error: Error) => {
      showSnackbar(error.message ?? 'Failed to add to Bet Tracker', 'error', { duration: 5000 })
    },
  })

  return {
    addToTracker: mutation.mutate,
    isAdding: mutation.isPending,
  }
}
