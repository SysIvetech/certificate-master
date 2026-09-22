'use client'

import Link from 'next/link'
import { AlertCircle, Search } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Suspense } from 'react'
import { LoginForm } from '@/components/auth/login-form'
import { AUTH_ENABLED } from '@/lib/auth/config'

export default function LoginPage() {
  // NEXT_PUBLIC_AUTH_ENABLED=true 일 때만 ivetech 통합 인증 폼 노출
  if (AUTH_ENABLED) {
    return (
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="max-w-lg w-full border-amber-500/20 bg-amber-500/5">
        <CardHeader>
          <div className="flex items-center gap-2 text-amber-400">
            <AlertCircle className="h-5 w-5" />
            <span className="text-sm font-medium">로그인 비활성화</span>
          </div>
          <CardTitle className="text-2xl text-foreground mt-2">
            현재 로그인 기능을 제공하지 않습니다
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-foreground/80">
          <p>
            이번 배포에서는 자격증 검색 기능만 이용할 수 있어요. 필요한 자격증 정보를 바로 찾아보세요.
          </p>
          <Button asChild className="w-full bg-emerald-600 hover:bg-emerald-700">
            <Link href="/">
              <Search className="mr-2 h-4 w-4" />
              자격증 검색으로 이동
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

