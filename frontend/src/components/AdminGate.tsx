import { type ReactNode, useState } from 'react'
import { Link } from 'react-router-dom'
import { isAdminGateEnabled, isAdminPageUnlocked, unlockAdminPage } from '../utils/adminGate'

export function AdminGate({ children }: { children: ReactNode }) {
  const [unlocked, setUnlocked] = useState(isAdminPageUnlocked)
  const [password, setPassword] = useState('')
  const [error, setError] = useState(false)

  if (!isAdminGateEnabled()) {
    return <>{children}</>
  }

  if (!unlocked) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm rounded-xl bg-surface-container border border-outline/20 shadow-sm p-6">
          <h1 className="text-lg font-black uppercase tracking-widest text-on-surface text-center">
            Admin access
          </h1>
          <p className="mt-2 text-xs text-on-surface-variant text-center">
            Enter the admin password to open the dashboard.
          </p>
          <form
            className="mt-6 space-y-4"
            onSubmit={(e) => {
              e.preventDefault()
              setError(false)
              if (unlockAdminPage(password)) {
                setUnlocked(true)
                setPassword('')
              } else {
                setError(true)
              }
            }}
          >
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              className="w-full px-3 py-2 rounded-lg bg-surface-container-high border border-outline/30 text-on-surface text-sm placeholder:text-on-surface-variant/60 focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
            {error && (
              <p className="text-xs text-error font-medium">Incorrect password.</p>
            )}
            <button
              type="submit"
              className="w-full py-2.5 rounded-lg bg-primary text-on-primary font-black text-xs uppercase tracking-widest hover:opacity-90 transition-opacity"
            >
              Continue
            </button>
          </form>
          <p className="mt-4 text-[10px] text-on-surface-variant/80 text-center">
            <Link to="/" className="text-primary-container hover:underline">
              Back to home
            </Link>
          </p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
