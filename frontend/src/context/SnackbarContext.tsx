import { createContext, useContext, useState, useCallback } from 'react'
import type { ReactNode } from 'react'
import { Snackbar } from '../components/Snackbar'
import type { SnackbarMessage, SnackbarType } from '../components/Snackbar'

interface SnackbarContextType {
  showSnackbar: (message: string, type: SnackbarType, options?: { progress?: number; duration?: number }) => void
  updateProgress: (progress: number) => void
  hideSnackbar: () => void
}

const SnackbarContext = createContext<SnackbarContextType | undefined>(undefined)

export function SnackbarProvider({ children }: { children: ReactNode }) {
  const [snackbar, setSnackbar] = useState<SnackbarMessage | null>(null)

  const showSnackbar = useCallback((message: string, type: SnackbarType, options?: { progress?: number; duration?: number }) => {
    const id = `snackbar-${Date.now()}-${Math.random()}`
    setSnackbar({
      id,
      message,
      type,
      progress: options?.progress,
      duration: options?.duration ?? (type === 'error' ? 5000 : 3000),
    })
  }, [])

  const updateProgress = useCallback((progress: number) => {
    setSnackbar((prev) => {
      if (!prev) return null
      return { ...prev, progress: Math.min(100, Math.max(0, progress)) }
    })
  }, [])

  const hideSnackbar = useCallback(() => {
    setSnackbar(null)
  }, [])

  return (
    <SnackbarContext.Provider value={{ showSnackbar, updateProgress, hideSnackbar }}>
      {children}
      <Snackbar snackbar={snackbar} onClose={hideSnackbar} />
    </SnackbarContext.Provider>
  )
}

export function useSnackbar() {
  const context = useContext(SnackbarContext)
  if (!context) {
    throw new Error('useSnackbar must be used within SnackbarProvider')
  }
  return context
}

