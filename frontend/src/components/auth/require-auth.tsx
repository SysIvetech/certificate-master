'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import { useAuthStore } from '@/stores/auth-store'
import { AUTH_ENABLED } from '@/lib/auth/config'

/**
 * 로그인이 필요한 페이지 가드 (클라이언트 측)
 *
 * access token이 메모리/localStorage에만 있어 Next.js middleware에서는
 * 로그인 여부를 알 수 없으므로 클라이언트에서 확인합니다.
 * 실제 데이터 보호는 백엔드의 JWT 검증(AUTH_ENABLED=true)이 담당합니다.
 *
 * NEXT_PUBLIC_AUTH_ENABLED=false 이면 아무 것도 하지 않습니다 (기존 동작).
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuthStore()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (AUTH_ENABLED && !isLoading && !user) {
      router.replace(`/login?redirectTo=${encodeURIComponent(pathname)}`)
    }
  }, [isLoading, user, router, pathname])

  if (!AUTH_ENABLED) return <>{children}</>

  if (isLoading || !user) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-emerald-400" aria-label="로그인 확인 중" />
      </div>
    )
  }

  return <>{children}</>
}
