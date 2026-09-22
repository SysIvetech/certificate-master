'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LogIn, LogOut, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/use-auth'
import { AUTH_ENABLED } from '@/lib/auth/config'

/**
 * 헤더 로그인/로그아웃 메뉴
 * NEXT_PUBLIC_AUTH_ENABLED=false 이면 렌더링하지 않습니다 (기존 헤더 그대로).
 */
export function AuthMenu() {
  const { user, isLoading, signOut } = useAuth()
  const pathname = usePathname()

  if (!AUTH_ENABLED || isLoading) return null

  if (!user) {
    const redirectTo = pathname && pathname !== '/login' ? `?redirectTo=${encodeURIComponent(pathname)}` : ''
    return (
      <Button asChild variant="ghost" size="sm" className="text-muted-foreground">
        <Link href={`/login${redirectTo}`}>
          <LogIn className="mr-1.5 h-4 w-4" />
          로그인
        </Link>
      </Button>
    )
  }

  return (
    <div className="flex items-center gap-1">
      <span className="hidden sm:flex items-center gap-1.5 text-sm text-muted-foreground max-w-[10rem] truncate">
        <User className="h-4 w-4 shrink-0" />
        <span className="truncate" data-testid="auth-user-name">
          {user.fullName || user.email}
        </span>
      </span>
      <Button variant="ghost" size="sm" onClick={signOut} className="text-muted-foreground">
        <LogOut className="mr-1.5 h-4 w-4" />
        로그아웃
      </Button>
    </div>
  )
}
