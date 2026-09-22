'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { Search, Grid3X3, List, Loader2, AlertCircle, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  CertificateCard,
  SearchInput
} from '@/components/certificate'
import { EmptyState } from '@/components/ui/empty-state'
import { ScrollToTop } from '@/components/ui/scroll-to-top'
import { useSearchStore } from '@/stores/search-store'
import { useInfiniteCertificates } from '@/hooks'
import { useDebounce } from '@/hooks/use-debounce'
import { cn } from '@/lib/utils'
import type { Certificate, CertificateList } from '@/lib/api'

export function HomeSearchContent() {
  const searchParams = useSearchParams()
  const initialQuery = searchParams.get('q') || ''
  const { query, setQuery } = useSearchStore()
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [userToggledView, setUserToggledView] = useState(false)

  // Set default view mode based on screen size (mobile = list, desktop = grid)
  useEffect(() => {
    if (userToggledView) return
    const mq = window.matchMedia('(min-width: 640px)')
    setViewMode(mq.matches ? 'grid' : 'list')
  }, [userToggledView])

  const handleViewModeChange = useCallback((mode: 'grid' | 'list') => {
    setUserToggledView(true)
    setViewMode(mode)
  }, [])

  // Infinite scroll observer
  const observerTarget = useRef<HTMLDivElement>(null)

  // Set initial query from URL
  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery)
    }
  }, [initialQuery, setQuery])

  // Debounce search parameters to reduce API calls
  const debouncedQuery = useDebounce(query, 300)

  // Fetch certificates with infinite scroll
  const {
    data,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteCertificates({
    q: debouncedQuery || undefined,
    page_size: 20,
  })

  // Flatten all pages into single array
  const results: Certificate[] = data?.pages ? data.pages.flatMap((page: CertificateList) => page.items) : []
  const totalCount: number = data?.pages && data.pages.length > 0 ? data.pages[0].total : 0

  // Set up intersection observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage()
        }
      },
      { threshold: 0.1 }
    )

    const currentTarget = observerTarget.current
    if (currentTarget) {
      observer.observe(currentTarget)
    }

    return () => {
      if (currentTarget) {
        observer.unobserve(currentTarget)
      }
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])

  const handleSearch = (newQuery: string) => {
    setQuery(newQuery)
  }

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section
        data-testid="home-hero"
        className="relative overflow-hidden border-b border-border"
      >
        {/* Background effects */}
        <div className="absolute inset-0 bg-gradient-to-b from-emerald-500/5 via-background to-background" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-emerald-500/10 via-transparent to-transparent" />
        {/* Glow orbs */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-[128px] animate-pulse-glow" />
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-[128px] animate-pulse-glow" style={{ animationDelay: '1s' }} />
        {/* Dot pattern */}
        <div className="absolute inset-0 pattern-dots opacity-[0.03]" />
        {/* Floating decorative elements */}
        <div className="absolute top-20 left-[10%] w-2 h-2 rounded-full bg-emerald-400/30 animate-float" />
        <div className="absolute top-32 right-[15%] w-1.5 h-1.5 rounded-full bg-cyan-400/30 animate-float" style={{ animationDelay: '2s' }} />
        <div className="absolute top-48 left-[20%] w-1 h-1 rounded-full bg-emerald-400/20 animate-float" style={{ animationDelay: '4s' }} />

        <div className="relative container mx-auto px-4 pt-12 pb-10 sm:pt-16 sm:pb-12">
          {/* Headline - with stagger animation */}
          <div className="text-center max-w-3xl mx-auto mb-8">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight mb-4 opacity-0 animate-slide-up">
              <span className="text-foreground">나에게 맞는</span>
              <span className="gradient-text">
                자격증
              </span>
              <span className="text-foreground">을 찾아보세요</span>
            </h1>
            <p className="text-base sm:text-lg text-muted-foreground leading-relaxed opacity-0 animate-slide-up stagger-1">
              600개 이상의 자격증 정보를 한눈에 비교하고,<br className="hidden sm:block" />
              AI 추천으로 내 상황에 딱 맞는 자격증을 발견하세요
            </p>
          </div>

          {/* Search Bar - with stagger */}
          <div className="max-w-2xl mx-auto mb-8 opacity-0 animate-slide-up stagger-2">
            <SearchInput
              initialQuery={query}
              onSearch={handleSearch}
              placeholder="자격증 이름을 입력하세요"
            />
          </div>

          {/* Quick Actions - with stagger */}
          <div className="flex flex-wrap items-center justify-center gap-3 mb-8 opacity-0 animate-slide-up stagger-3">
            <Link
              href="/recommend"
              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 transition-[box-shadow,transform] hover:-translate-y-0.5"
            >
              <Sparkles className="h-4 w-4" />
              AI 추천 받기
            </Link>
            <Link
              href="/about"
              className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/50 px-6 py-3 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              서비스 소개
            </Link>
          </div>
        </div>
      </section>

      {/* Search Results Section */}
      <div className="py-8">
        <div className="container mx-auto px-4">

        <div className="flex flex-col gap-8">
          {/* Results */}
          <div>
            {/* API Error State */}
            {error && !isLoading && (
              <EmptyState
                icon={AlertCircle}
                title="데이터를 불러올 수 없습니다"
                description="서버와의 연결에 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
                action={{
                  label: '다시 시도',
                  onClick: () => window.location.reload(),
                }}
              />
            )}

            {/* Results Header */}
            {!error && !isLoading && (
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className="border-border text-foreground">
                    {totalCount > 0 ? `${totalCount}개 결과` : '0개 결과'}
                  </Badge>
                  {query && (
                    <span className="text-muted-foreground">
                      &quot;{query}&quot; 검색 결과
                    </span>
                  )}
                </div>

                {/* View Mode Toggle */}
                {results.length > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground hidden sm:inline">
                      보기 방식
                    </span>
                    <div className="flex rounded-lg bg-muted/50 p-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="그리드 보기"
                        onClick={() => handleViewModeChange('grid')}
                        className={cn(
                          'h-8 w-8',
                          viewMode === 'grid'
                            ? 'bg-muted text-foreground'
                            : 'text-muted-foreground hover:text-foreground'
                        )}
                      >
                        <Grid3X3 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="리스트 보기"
                        onClick={() => handleViewModeChange('list')}
                        className={cn(
                          'h-8 w-8',
                          viewMode === 'list'
                            ? 'bg-muted text-foreground'
                            : 'text-muted-foreground hover:text-foreground'
                        )}
                      >
                        <List className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Initial Loading State */}
            {isLoading && results.length === 0 && (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            )}

            {/* No Results */}
            {!error && !isLoading && results.length === 0 && (
              <EmptyState
                icon={Search}
                title={query ? '검색 결과가 없습니다' : '자격증을 검색해보세요'}
                description={
                  query
                    ? '다른 검색어를 입력해보세요.'
                    : '위의 검색창에 원하는 자격증명을 입력하세요.'
                }
                action={
                  query
                    ? {
                        label: '검색 초기화',
                        onClick: () => setQuery(''),
                      }
                    : undefined
                }
              />
            )}

            {/* Results Grid */}
            {!error && results.length > 0 && (
              <>
                <div
                  className={cn(
                    'grid',
                    viewMode === 'grid'
                      ? 'gap-6 grid-cols-1 sm:grid-cols-2 xl:grid-cols-3'
                      : 'gap-3 grid-cols-1'
                  )}
                >
                  {results.map((cert, index) => (
                    <div
                      key={cert.id}
                      className="opacity-0 animate-slide-up card-lazy-render"
                      style={{ animationDelay: `${(index % 20) * 0.05}s` }}
                    >
                      <CertificateCard
                        id={cert.id}
                        slug={cert.slug}
                        title={cert.title}
                        categories={cert.categories}
                        difficulty={cert.difficulty ?? null}
                        passRate={cert.passing_rate ? cert.passing_rate / 100 : null}
                        studyPeriod={cert.study_period_days ?? null}
                        overview={cert.overview ?? null}
                        variant={viewMode}
                      />
                    </div>
                  ))}
                </div>

                {/* Infinite Scroll Trigger & Loading Indicator */}
                <div
                  ref={observerTarget}
                  data-testid="infinite-scroll-trigger"
                  className="mt-8 flex justify-center items-center min-h-[60px]"
                >
                  {isFetchingNextPage && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="h-5 w-5 animate-spin" />
                      <span>더 많은 결과를 불러오는 중\u2026</span>
                    </div>
                  )}
                  {!hasNextPage && results.length > 0 && (
                    <div className="text-muted-foreground text-sm">
                      모든 결과를 불러왔습니다 ({totalCount}개)
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
      </div>

      {/* Mobile scroll-to-top button */}
      <ScrollToTop />
    </div>
  )
}
