'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth-store'
import { userFromAccessToken } from '@/lib/auth/auth-api'
import { tokenManager } from '@/lib/auth/token-manager'
import { AUTH_ENABLED, POST_LOGIN_REDIRECT_KEY, sanitizeRedirectPath } from '@/lib/auth/config'

/**
 * ivetech 인증 서비스 OAuth2(Google) 로그인 콜백
 *
 * auth-service가 로그인 성공 시 다음 형태로 리다이렉트합니다.
 *   /oauth/callback#access_token=...&refresh_token=...
 * 실패 시:
 *   /oauth/callback?error=...
 *
 * 토큰은 URL fragment(#)로 전달되므로 서버 로그/Referer에 남지 않으며,
 * 읽은 즉시 주소창에서 제거합니다.
 */
export default function OAuthCallbackPage() {
  const router = useRouter()
  const { setUser } = useAuthStore()
  const [error, setError] = useState<string | null>(null)
  const processed = useRef(false)

  useEffect(() => {
    // React StrictMode 이중 실행 방지
    if (processed.current) return
    processed.current = true

    const { hash, search, pathname } = window.location
    // 토큰이 주소창/히스토리에 남지 않도록 즉시 제거
    window.history.replaceState(null, '', pathname)

    if (!AUTH_ENABLED) {
      router.replace('/')
      return
    }

    const oauthError = new URLSearchParams(search).get('error')
    if (oauthError) {
      setError('Google 로그인에 실패했습니다. 다시 시도해주세요.')
      return
    }

    const params = new URLSearchParams(hash.replace(/^#/, ''))
    const accessToken = params.get('access_token')
    const refreshToken = params.get('refresh_token')
    const user = userFromAccessToken(accessToken)

    if (!accessToken || !user) {
      setError('로그인 정보를 확인할 수 없습니다. 다시 시도해주세요.')
      return
    }

    tokenManager.setTokens(accessToken, refreshToken)
    setUser(user)

    let redirectTo = '/'
    try {
      redirectTo = sanitizeRedirectPath(sessionStorage.getItem(POST_LOGIN_REDIRECT_KEY))
      sessionStorage.removeItem(POST_LOGIN_REDIRECT_KEY)
    } catch {
      // sessionStorage 접근 불가 시 홈으로 이동
    }
    router.replace(redirectTo)
  }, [router, setUser])

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-4 text-center">
        <div className="flex items-center gap-2 text-red-400">
          <AlertCircle className="h-5 w-5" />
          <p>{error}</p>
        </div>
        <Button asChild className="bg-emerald-600 hover:bg-emerald-700">
          <Link href="/login">로그인 페이지로 이동</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4">
      <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      <p className="text-muted-foreground">로그인 처리 중…</p>
    </div>
  )
}
