'use client'

import { useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth-store'
import { AUTH_ENABLED } from '@/lib/auth/config'
import { getAccessToken, logout as logoutRequest, userFromAccessToken } from '@/lib/auth/auth-api'
import type { AuthUser } from '@/types'

interface UseAuthReturn {
  user: AuthUser | null
  isLoading: boolean
  isAuthenticated: boolean
  signOut: () => Promise<void>
  checkSession: () => Promise<void>
}

/**
 * ivetech 통합 인증 서비스 기반 인증 상태 훅
 *
 * access token은 메모리에만 있으므로 새로고침 후에는 refresh token으로
 * 재발급받아 로그인 상태를 복원합니다 (checkSession).
 */
export function useAuth(): UseAuthReturn {
  const { user, isLoading, setUser, logout } = useAuthStore()
  const router = useRouter()

  const checkSession = useCallback(async () => {
    if (!AUTH_ENABLED) {
      logout()
      return
    }
    try {
      const token = await getAccessToken()
      const restored = userFromAccessToken(token)
      if (restored) {
        setUser(restored)
      } else {
        logout()
      }
    } catch (error) {
      console.error('Session check error:', error)
      logout()
    }
  }, [logout, setUser])

  const signOut = useCallback(async () => {
    await logoutRequest()
    logout()
    router.push('/')
    router.refresh()
  }, [logout, router])

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    signOut,
    checkSession,
  }
}
