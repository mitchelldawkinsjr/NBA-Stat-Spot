/**
 * Loading Spinner Component
 * Professional loading animation with Sliced theme styling
 */
export function LoadingSpinner({ message = 'Loading...', size = 'md' }: { message?: string; size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-12 h-12',
    lg: 'w-16 h-16'
  }

  const borderClasses = {
    sm: 'border-2',
    md: 'border-3',
    lg: 'border-4'
  }

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      {/* Spinner with professional gradient look */}
      <div className="relative mb-6">
        {/* Outer glow ring for depth and elegance */}
        <div 
          className={`absolute inset-0 ${sizeClasses[size]} border-blue-400/20 rounded-full blur-xl animate-pulse`}
        />
        {/* Main spinner - clean gradient border */}
        <div className="relative">
          <div 
            className={`${sizeClasses[size]} ${borderClasses[size]} rounded-full animate-spin`}
            style={{
              background: `conic-gradient(from 0deg, transparent 0deg, transparent 270deg, #3b82f6 270deg, #8b5cf6 315deg, #ec4899 360deg)`,
              padding: size === 'sm' ? '2px' : size === 'md' ? '3px' : '4px',
            }}
          >
            <div className="w-full h-full rounded-full bg-white dark:bg-gray-900"></div>
          </div>
        </div>
        {/* Inner glow pulse for depth */}
        <div 
          className={`absolute inset-3 ${size === 'sm' ? 'w-1 h-1' : size === 'md' ? 'w-3 h-3' : 'w-4 h-4'} bg-gradient-to-br from-blue-400/30 to-purple-400/30 rounded-full animate-pulse`}
        />
      </div>
      
      {/* Loading text with elegant gradient */}
      <p className="text-base font-semibold bg-gradient-to-r from-slate-700 dark:from-slate-300 via-blue-600 dark:via-blue-400 to-slate-700 dark:to-slate-300 bg-clip-text text-transparent mb-5 tracking-wide transition-colors duration-200">
        {message}
      </p>
      
      {/* Enhanced progress bar with gradient and shine */}
      <div className="w-64 h-2.5 bg-gradient-to-r from-gray-100 dark:from-slate-700 to-gray-50 dark:to-slate-800 rounded-full overflow-hidden shadow-inner border border-gray-200/60 dark:border-slate-600/60 relative transition-colors duration-200">
        <div 
          className="h-full bg-gradient-to-r from-blue-500 via-purple-500 via-pink-500 to-blue-500 rounded-full animate-progress relative"
          style={{
            backgroundSize: '200% 100%',
            backgroundPosition: '0% 0%',
          }}
        >
          {/* Shine effect overlay */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-shimmer"></div>
        </div>
      </div>
    </div>
  )
}

/**
 * Loading Skeleton Component
 * Shows placeholder content while loading
 */
export function LoadingSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="flex space-x-4">
          <div className="flex-1 space-y-2 py-1">
            <div className="h-4 bg-gradient-to-r from-gray-200 dark:from-slate-700 via-gray-100 dark:via-slate-600 to-gray-200 dark:to-slate-700 rounded w-3/4 transition-colors duration-200"></div>
            <div className="h-4 bg-gradient-to-r from-gray-200 dark:from-slate-700 via-gray-100 dark:via-slate-600 to-gray-200 dark:to-slate-700 rounded w-1/2 transition-colors duration-200"></div>
          </div>
        </div>
      ))}
    </div>
  )
}

/**
 * Full Page Loading Component
 * Professional loading screen with enhanced visuals and progress indicator
 */
export function PageLoader({ message = 'Loading player data...', progress }: { message?: string; progress?: number }) {
  const displayProgress = progress !== undefined ? progress : 0
  
  return (
    <div className="min-h-[500px] flex items-center justify-center bg-gradient-to-br from-gray-50 dark:from-slate-900 via-white dark:via-slate-800 to-blue-50/30 dark:to-blue-900/20 rounded-xl shadow-lg ring-1 ring-gray-200/50 dark:ring-slate-700/50 p-12 relative overflow-hidden transition-colors duration-200">
      {/* Background decorative elements */}
      <div className="absolute inset-0 opacity-5 dark:opacity-10">
        <div className="absolute top-10 left-10 w-32 h-32 bg-blue-500 dark:bg-blue-400 rounded-full blur-3xl"></div>
        <div className="absolute bottom-10 right-10 w-40 h-40 bg-purple-500 dark:bg-purple-400 rounded-full blur-3xl"></div>
      </div>
      
      <div className="text-center relative z-10 w-full max-w-md">
        <LoadingSpinner message={message} size="lg" />
        
        {/* Progress percentage display */}
        {progress !== undefined && (
          <div className="mt-6">
            <div className="text-3xl font-bold bg-gradient-to-r from-blue-600 dark:from-blue-400 via-purple-600 dark:via-purple-400 to-pink-600 dark:to-pink-400 bg-clip-text text-transparent mb-3 transition-colors duration-200">
              {displayProgress}%
            </div>
            {/* Progress bar */}
            <div className="w-full max-w-xs mx-auto h-3 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden shadow-inner transition-colors duration-200">
              <div 
                className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full transition-all duration-500 ease-out relative"
                style={{ width: `${displayProgress}%` }}
              >
                {/* Shine effect */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 dark:via-white/20 to-transparent animate-shimmer"></div>
              </div>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 transition-colors duration-200">Fetching player data from backend...</p>
          </div>
        )}
        
        {/* Enhanced loading dots with gradient */}
        {progress === undefined && (
          <div className="flex justify-center gap-2 mt-6">
            <div 
              className="w-2.5 h-2.5 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full animate-bounce shadow-sm" 
              style={{ animationDelay: '0ms', animationDuration: '1.4s' }}
            ></div>
            <div 
              className="w-2.5 h-2.5 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full animate-bounce shadow-sm" 
              style={{ animationDelay: '200ms', animationDuration: '1.4s' }}
            ></div>
            <div 
              className="w-2.5 h-2.5 bg-gradient-to-br from-pink-500 to-blue-500 rounded-full animate-bounce shadow-sm" 
              style={{ animationDelay: '400ms', animationDuration: '1.4s' }}
            ></div>
          </div>
        )}
      </div>
    </div>
  )
}
