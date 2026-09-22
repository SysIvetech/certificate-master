'use client'

import Link from 'next/link'
import { AlertCircle, Search } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { SignupForm } from '@/components/auth/signup-form'
import { AUTH_ENABLED } from '@/lib/auth/config'

export default function SignupPage() {
  // NEXT_PUBLIC_AUTH_ENABLED=true 일 때만 ivetech 통합 인증 폼 노출
  if (AUTH_ENABLED) {
    return (
      <SignupForm />
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="max-w-lg w-full border-amber-500/20 bg-amber-500/5">
        <CardHeader>
          <div className="flex items-center gap-2 text-amber-400">
            <AlertCircle className="h-5 w-5" />
            <span className="text-sm font-medium">회원가입 준비 중</span>
          </div>
          <CardTitle className="text-2xl text-foreground mt-2">
            회원가입 기능을 준비하고 있어요
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-foreground/80">
          <p>
            자격증 검색만 제공하는 기간이라 회원가입 기능을 잠시 닫아두었습니다.
            검색 결과와 상세 정보는 바로 확인할 수 있어요.
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

