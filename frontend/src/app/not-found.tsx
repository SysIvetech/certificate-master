import Link from 'next/link'
import { Search, Home } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center px-4 py-16">
      <div className="text-center max-w-md">
        <div className="flex items-center justify-center mb-6">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted/50 border border-border">
            <Search className="h-10 w-10 text-muted-foreground" />
          </div>
        </div>

        <h1 className="text-3xl font-bold text-foreground mb-3">
          페이지를 찾을 수 없습니다
        </h1>
        <p className="text-muted-foreground mb-8 leading-relaxed">
          요청하신 페이지가 존재하지 않거나 이동되었을 수 있습니다.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button asChild className="bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-900 font-semibold hover:from-emerald-400 hover:to-cyan-400">
            <Link href="/">
              <Home className="mr-2 h-4 w-4" />
              홈으로 돌아가기
            </Link>
          </Button>
          <Button asChild variant="outline" className="border-border text-foreground/80 hover:bg-muted">
            <Link href="/recommend">
              AI 자격증 추천 받기
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}
