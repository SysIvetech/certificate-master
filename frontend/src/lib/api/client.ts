/**
 * API Client
 * 
 * Centralized HTTP client for backend API communication.
 * 인증: ivetech 통합 인증 서비스(auth-service) access token (lib/auth).
 */

import { AUTH_ENABLED } from '@/lib/auth/config'
import { getAccessToken, refreshAccessToken } from '@/lib/auth/auth-api'
import { tokenManager } from '@/lib/auth/token-manager'

// 항상 상대 경로 사용 (Next.js rewrites로 프록시)
// 이렇게 하면 로컬 네트워크 접근 권한이 필요 없음
// 브라우저 → /api/* (같은 origin) → Next.js 서버 → 백엔드
const API_URL = '';

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown
  ) {
    super(message)
    this.name = 'APIError'
  }
}

/**
 * ivetech auth-service access token으로 인증 헤더를 만듭니다.
 * 로그인하지 않았거나 인증이 비활성화된 경우 인증 헤더 없이 요청합니다.
 */
async function getAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (!AUTH_ENABLED) return headers

  const token = await getAccessToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_URL}${endpoint}`
  
  console.log('=' .repeat(80))
  console.log('📡 [API Client] Fetching:', options.method || 'GET', endpoint)
  console.log('🌐 [API Client] Full URL:', url)
  
  // Get auth headers
  const authHeaders = await getAuthHeaders()
  
  const config: RequestInit = {
    ...options,
    headers: {
      ...authHeaders,
      ...options.headers, // Allow override if needed
    },
  }

  // Log request details
  const headers = config.headers as Record<string, string> | undefined
  console.log('📤 [API Client] Request headers:', {
    Authorization: headers?.['Authorization'] ? 'Bearer (present)' : 'N/A',
    'Content-Type': headers?.['Content-Type'] || 'N/A',
  })
  
  if (options.body) {
    try {
      const parsedBody = typeof options.body === 'string'
        ? JSON.parse(options.body)
        : options.body
      console.log('📦 [API Client] Request body:', parsedBody)
    } catch {
      console.log('📦 [API Client] Request body: [unparsed]')
    }
  }

  try {
    console.log('⏳ [API Client] Sending request...')
    let response = await fetch(url, config)

    // access token 만료 등으로 401이면 refresh 후 한 번만 재시도
    if (response.status === 401 && AUTH_ENABLED && tokenManager.getRefreshToken()) {
      const newToken = await refreshAccessToken()
      if (newToken) {
        response = await fetch(url, {
          ...config,
          headers: { ...(config.headers as Record<string, string>), Authorization: `Bearer ${newToken}` },
        })
      }
    }

    console.log('📥 [API Client] Response received:', {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
      headers: {
        'access-control-allow-origin': response.headers.get('access-control-allow-origin'),
        'content-type': response.headers.get('content-type'),
      }
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({})) as unknown
      console.error('❌ [API Client] Error response:', {
        status: response.status,
        statusText: response.statusText,
        errorData
      })

      // Log detail array if present
      if (
        typeof errorData === 'object' &&
        errorData !== null &&
        Array.isArray((errorData as { detail?: unknown }).detail)
      ) {
        const details = (errorData as { detail: unknown[] }).detail
        console.error('📋 [API Client] Validation errors:')
        details.forEach((err, idx) => {
          console.error(`  ${idx + 1}.`, err)
        })
      }

      console.log('=' .repeat(80))
      const errorDetail = (errorData as { detail?: string })?.detail
      throw new APIError(
        errorDetail || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      )
    }

    // Handle 204 No Content
    if (response.status === 204) {
      console.log('✅ [API Client] Success (204 No Content)')
      console.log('=' .repeat(80))
      return undefined as T
    }

    const data = await response.json()
    console.log('✅ [API Client] Success:', data)
    console.log('=' .repeat(80))
    return data
  } catch (error) {
    console.error('💥 [API Client] Fetch failed:', error)
    console.log('=' .repeat(80))
    if (error instanceof APIError) {
      throw error
    }
    throw new APIError(
      error instanceof Error ? error.message : 'Unknown error occurred',
      0
    )
  }
}

export const api = {
  get: <T>(endpoint: string) => fetchAPI<T>(endpoint, { method: 'GET' }),
  
  post: <T, B = unknown>(endpoint: string, data: B) =>
    fetchAPI<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  patch: <T, B = unknown>(endpoint: string, data: B) =>
    fetchAPI<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  
  delete: <T>(endpoint: string) =>
    fetchAPI<T>(endpoint, { method: 'DELETE' }),
}
