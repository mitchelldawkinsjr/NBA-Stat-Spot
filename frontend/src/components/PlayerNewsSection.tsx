import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { apiFetch } from '../utils/api'

interface NewsArticle {
  headline?: string
  title?: string
  description?: string
  published?: string
  publishDate?: string
  links?: {
    web?: {
      href: string
    }
    mobile?: {
      href: string
    }
  }
  images?: Array<{
    url: string
    alt?: string
    caption?: string
  }>
  [key: string]: any // Allow for additional ESPN API fields
}

async function fetchPlayerNews() {
  const res = await apiFetch('api/v1/espn/news')
  if (!res.ok) {
    throw new Error('Failed to load news')
  }
  const data = await res.json()
  // ESPN router returns { articles: [...] }
  return data.articles || []
}

export function PlayerNewsSection() {
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const scrollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const isPausedRef = useRef(false)

  const { data: news, isLoading, error } = useQuery<NewsArticle[]>({
    queryKey: ['player-news'],
    queryFn: fetchPlayerNews,
    staleTime: 15 * 60 * 1000, // 15 minutes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    retry: 1,
  })

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return ''
    try {
      const date = new Date(dateStr)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
      const diffDays = Math.floor(diffHours / 24)

      if (diffHours < 1) return 'Just now'
      if (diffHours < 24) return `${diffHours}h ago`
      if (diffDays === 1) return 'Yesterday'
      if (diffDays < 7) return `${diffDays}d ago`
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    } catch {
      return ''
    }
  }

  const displayedNews = news?.slice(0, 8) || []

  // Auto-scroll functionality
  useEffect(() => {
    if (!scrollContainerRef.current || displayedNews.length === 0) return

    const container = scrollContainerRef.current
    let scrollPosition = 0
    const scrollSpeed = 0.5 // pixels per frame
    const scrollDelay = 20 // milliseconds between scrolls

    const startAutoScroll = () => {
      if (scrollIntervalRef.current) {
        clearInterval(scrollIntervalRef.current)
      }

      scrollIntervalRef.current = setInterval(() => {
        if (isPausedRef.current) return

        const maxScroll = container.scrollWidth - container.clientWidth
        scrollPosition += scrollSpeed

        if (scrollPosition >= maxScroll) {
          // Reset to beginning for continuous loop
          scrollPosition = 0
          container.scrollTo({ left: 0, behavior: 'auto' })
        } else {
          container.scrollTo({ left: scrollPosition, behavior: 'auto' })
        }
      }, scrollDelay)
    }

    // Pause on hover
    const handleMouseEnter = () => {
      isPausedRef.current = true
    }

    const handleMouseLeave = () => {
      isPausedRef.current = false
    }

    container.addEventListener('mouseenter', handleMouseEnter)
    container.addEventListener('mouseleave', handleMouseLeave)

    startAutoScroll()

    return () => {
      if (scrollIntervalRef.current) {
        clearInterval(scrollIntervalRef.current)
      }
      container.removeEventListener('mouseenter', handleMouseEnter)
      container.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [displayedNews.length])

  return (
    <>
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 transition-colors duration-200">
            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span className="text-sm">Loading news…</span>
          </div>
        </div>
      ) : error ? (
        <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg transition-colors duration-200">
          <p className="text-xs text-yellow-800 dark:text-yellow-300 transition-colors duration-200">Unable to load news. News feed may be temporarily unavailable.</p>
        </div>
      ) : displayedNews.length === 0 ? (
        <p className="text-gray-600 dark:text-gray-400 text-center py-4 text-sm transition-colors duration-200">No recent news available.</p>
      ) : (
        <div 
          ref={scrollContainerRef}
          className="overflow-x-auto -mx-4 px-4 pb-1 sm:pb-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100" 
          style={{ scrollbarWidth: 'thin' }}
        >
          <div className="flex gap-2 sm:gap-3 min-w-max">
            {displayedNews.map((article, idx) => {
              const articleUrl = article.links?.web?.href || article.links?.mobile?.href || '#'
              const imageUrl = article.images?.[0]?.url
              const isExternal = articleUrl.startsWith('http')
              const headline = article.headline || article.title || 'No title'
              const published = article.published || article.publishDate

              return (
                <div
                  key={idx}
                  className="flex-none w-40 sm:w-48 md:w-56 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-sm hover:shadow-md hover:border-blue-300 dark:hover:border-blue-600 transition-all duration-200 overflow-hidden"
                >
                  {isExternal ? (
                    <a
                      href={articleUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block group h-full"
                    >
                      {imageUrl && (
                        <div className="w-full aspect-[16/9] sm:aspect-[16/9] bg-gray-200 dark:bg-slate-700 overflow-hidden rounded-t-lg">
                          <img
                            src={imageUrl}
                            alt={article.images?.[0]?.alt || article.images?.[0]?.caption || headline}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                            style={{ objectPosition: 'center' }}
                            onError={(e) => {
                              e.currentTarget.style.display = 'none'
                            }}
                          />
                        </div>
                      )}
                      <div className="p-1 sm:p-1.5 md:p-2">
                        <h4 className="text-[9px] sm:text-[10px] md:text-xs font-semibold text-gray-900 dark:text-slate-100 group-hover:text-blue-700 dark:group-hover:text-blue-400 line-clamp-2 mb-0.5 sm:mb-1 transition-colors duration-200 leading-tight">
                          {headline}
                        </h4>
                        {article.description && (
                          <p className="hidden sm:block text-[9px] md:text-[10px] text-gray-600 dark:text-gray-400 line-clamp-2 mb-0.5 sm:mb-1 transition-colors duration-200 leading-tight">
                            {article.description}
                          </p>
                        )}
                        <div className="flex items-center justify-between text-[8px] sm:text-[9px] md:text-[10px] text-gray-500 dark:text-gray-400 transition-colors duration-200 mt-0.5 sm:mt-1">
                          {published && <span>{formatDate(published)}</span>}
                          <span className="text-blue-600 dark:text-blue-400 group-hover:text-blue-800 dark:group-hover:text-blue-300 font-medium transition-colors duration-200">
                            →
                          </span>
                        </div>
                      </div>
                    </a>
                  ) : (
                    <div className="h-full">
                      {imageUrl && (
                        <div className="w-full aspect-[16/9] sm:aspect-[16/9] bg-gray-200 dark:bg-slate-700 overflow-hidden rounded-t-lg">
                          <img
                            src={imageUrl}
                            alt={article.images?.[0]?.alt || article.images?.[0]?.caption || headline}
                            className="w-full h-full object-cover"
                            style={{ objectPosition: 'center' }}
                            onError={(e) => {
                              e.currentTarget.style.display = 'none'
                            }}
                          />
                        </div>
                      )}
                      <div className="p-1 sm:p-1.5 md:p-2">
                        <h4 className="text-[9px] sm:text-[10px] md:text-xs font-semibold text-gray-900 dark:text-slate-100 line-clamp-2 mb-0.5 sm:mb-1 transition-colors duration-200 leading-tight">
                          {headline}
                        </h4>
                        {article.description && (
                          <p className="hidden sm:block text-[9px] md:text-[10px] text-gray-600 dark:text-gray-400 line-clamp-2 mb-0.5 sm:mb-1 transition-colors duration-200 leading-tight">
                            {article.description}
                          </p>
                        )}
                        {published && (
                          <div className="text-[8px] sm:text-[9px] md:text-[10px] text-gray-500 dark:text-gray-400 transition-colors duration-200 mt-0.5 sm:mt-1">
                            {formatDate(published)}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </>
  )
}

