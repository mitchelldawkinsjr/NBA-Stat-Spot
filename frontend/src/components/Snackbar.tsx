import { useEffect, useState, useRef } from 'react'

export type SnackbarType = 'success' | 'error' | 'info' | 'warning'

export interface SnackbarMessage {
  id: string
  message: string
  type: SnackbarType
  progress?: number // 0-100 for progress bar
  duration?: number // Auto-dismiss duration in ms
}

interface SnackbarProps {
  snackbar: SnackbarMessage | null
  onClose: () => void
}

export function Snackbar({ snackbar, onClose }: SnackbarProps) {
  const [progress, setProgress] = useState(0)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  // Reset progress when snackbar changes
  useEffect(() => {
    if (!snackbar) {
      setProgress(0)
      return
    }

    // Reset progress when snackbar ID changes (new snackbar)
    setProgress(snackbar.progress ?? 0)
  }, [snackbar?.id])

  // Update progress bar when progress value changes
  useEffect(() => {
    if (!snackbar || snackbar.progress === undefined) return
    setProgress(snackbar.progress)
  }, [snackbar?.progress])

  // Auto-dismiss timer
  useEffect(() => {
    // Clear any existing timer first
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }

    if (!snackbar) return

    // Auto-dismiss if duration is set and not showing progress
    if (snackbar.duration && snackbar.progress === undefined) {
      timerRef.current = setTimeout(() => {
        onClose()
        timerRef.current = null
      }, snackbar.duration)
    }

    // Note: We don't auto-dismiss when progress reaches 100% to allow
    // manual control (e.g., showing a success message after completion)
    // The parent component should call hideSnackbar() when ready

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [snackbar?.id, snackbar?.duration, snackbar?.progress, onClose])

  if (!snackbar) return null

  const typeStyles = {
    success: 'bg-green-500 text-white border-green-600',
    error: 'bg-red-500 text-white border-red-600',
    info: 'bg-blue-500 text-white border-blue-600',
    warning: 'bg-amber-500 text-white border-amber-600',
  }

  const iconStyles = {
    success: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
    error: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
    info: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
  }

  return (
    <div
      className={`fixed bottom-5 right-5 z-[9999] min-w-[320px] max-w-md rounded-lg shadow-lg border-2 ${typeStyles[snackbar.type]} transition-all duration-300 ease-out`}
      style={{
        transform: 'translateY(0)',
        opacity: 1,
      }}
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-0.5">
            {iconStyles[snackbar.type]}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium">{snackbar.message}</p>
            {/* Progress bar */}
            {snackbar.progress !== undefined && (
              <div className="mt-3">
                <div className="w-full bg-white/20 rounded-full h-2 overflow-hidden">
                  <div
                    className="h-full bg-white transition-all duration-300 ease-out rounded-full"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-xs mt-1 opacity-90">{Math.round(progress)}%</p>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 text-white/80 hover:text-white transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

