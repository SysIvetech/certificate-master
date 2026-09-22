'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  GraduationCap,
  Search,
  Sparkles,
} from 'lucide-react'
import dynamic from 'next/dynamic'
import { cn } from '@/lib/utils'
import { ThemeToggle } from '@/components/ui/theme-toggle'
import { AuthMenu } from './auth-menu'

// 모바일 메뉴를 lazy-load하여 @radix-ui/react-dialog를 초기 번들에서 제거 (~20+ KiB 절감)
const MobileNav = dynamic(
  () => import('./mobile-nav').then((mod) => ({ default: mod.MobileNav })),
  { ssr: false }
)

const navItems = [
  { href: '/', label: '자격증 검색', icon: Search },
  { href: '/recommend', label: 'AI 추천', icon: Sparkles },
]

export function Header() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="container mx-auto flex h-16 items-center px-4">
        {/* Logo */}
        <Link href="/" className="mr-8 flex items-center space-x-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-400 to-cyan-500">
            <GraduationCap className="h-5 w-5 text-white" />
          </div>
          <span className="font-bold text-lg tracking-tight text-foreground">
            자격증 마스터
          </span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex md:flex-1 md:items-center md:gap-6">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-2 text-sm font-medium transition-colors hover:text-emerald-600 dark:hover:text-emerald-400',
                  pathname === item.href
                    ? 'text-primary'
                    : 'text-muted-foreground'
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            )
          })}
        </nav>

        {/* Auth Menu, Theme Toggle & Mobile Menu */}
        <div className="flex items-center gap-2 ml-auto md:ml-0">
          <AuthMenu />
          <ThemeToggle />
          <MobileNav navItems={navItems} />
        </div>
      </div>
    </header>
  )
}
