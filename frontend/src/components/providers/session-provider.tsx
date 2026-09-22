'use client'

import { useEffect } from 'react'
import { useAuth } from '@/hooks/use-auth'

interface SessionProviderProps {
  children: React.ReactNode
}

/**
 * SessionProvider
 *
 * 앱 로드 시 ivetech 인증 서비스 세션(refresh token)을 확인하고 auth store와 동기화합니다.
 * 모든 페이지에서 로그인 상태를 확인할 수 있도록 root layout에 추가하세요.
 */
export function SessionProvider({ children }: SessionProviderProps) {
  const { checkSession } = useAuth()

  useEffect(() => {
    // 앱 로드 시 세션 체크
    checkSession()
  }, [checkSession])

  return <>{children}</>
}
