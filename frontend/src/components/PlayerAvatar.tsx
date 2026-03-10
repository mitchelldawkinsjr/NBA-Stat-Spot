import { useState } from 'react'
import { getPlayerHeadshotUrl } from '../utils/playerHeadshot'

type PlayerAvatarProps = {
  playerId: number
  playerName?: string
  /** small: 6 (24px), medium: 8 (32px), large: 12 (48px) */
  size?: 'small' | 'medium' | 'large'
  className?: string
}

const sizeClasses = {
  small: 'h-6 w-6 text-[10px]',
  medium: 'h-8 w-8 text-xs',
  large: 'h-12 w-12 text-base',
}

export function PlayerAvatar({ playerId, playerName, size = 'small', className = '' }: PlayerAvatarProps) {
  const [errored, setErrored] = useState(false)
  const validId = Number.isFinite(Number(playerId)) && Number(playerId) > 0
  const url = validId ? getPlayerHeadshotUrl(playerId, size === 'large' ? '1040x760' : '260x190') : ''
  const initial = (playerName || 'P').slice(0, 1).toUpperCase()
  const sizeClass = sizeClasses[size]

  if (!url || errored) {
    return (
      <div
        className={`rounded-full bg-slate-200 dark:bg-slate-600 flex items-center justify-center font-semibold text-slate-700 dark:text-slate-200 flex-shrink-0 ${sizeClass} ${className}`}
        aria-hidden
      >
        {initial}
      </div>
    )
  }

  return (
    <img
      src={url}
      alt=""
      className={`rounded-full object-cover bg-slate-100 dark:bg-slate-700 flex-shrink-0 ${sizeClass} ${className}`}
      onError={() => setErrored(true)}
    />
  )
}
