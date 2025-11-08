/**
 * Cache Utility - Backward Compatibility Re-export
 * 
 * This file re-exports from the new cache system for backward compatibility.
 * The new system supports pluggable cache providers.
 * 
 * To switch cache providers, import setCacheProvider from './cache' and call:
 *   import { setCacheProvider } from './utils/cache'
 *   setCacheProvider('localStorage') // or 'memory', or a custom provider
 * 
 * @deprecated Import directly from './cache' for new code
 */

// Re-export everything from the new cache system
export * from './cache/index'

