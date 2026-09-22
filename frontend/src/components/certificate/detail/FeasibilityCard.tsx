'use client'

import {
  Users,
  CheckCircle,
  XCircle,
  Clock,
  Briefcase,
  Target,
  TrendingUp,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import type { FeasibilityInfo } from '@/lib/api/types'
import { cn } from '@/lib/utils'

interface FeasibilityCardProps {
  feasibilityInfo: FeasibilityInfo
  className?: string
}

/**
 * FeasibilityCard - 합격 가능성 분석 카드
 *
 * 비전공자 합격률, 독학 가능 여부, 최소 준비 기간 등을 표시합니다.
 */
export function FeasibilityCard({ feasibilityInfo, className }: FeasibilityCardProps) {
  const hasAnyData =
    feasibilityInfo.non_major_pass_rate ||
    feasibilityInfo.self_study_possible !== null ||
    feasibilityInfo.minimum_study_period !== null ||
    feasibilityInfo.first_attempt_pass_rate ||
    (feasibilityInfo.working_adult_tips?.length ?? 0) > 0

  if (!hasAnyData) return null

  return (
    <Card className={cn('bg-card/50 border-border', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Target className="h-5 w-5 text-emerald-400" />
          합격 가능성 분석
        </CardTitle>
        <CardDescription>
          비전공자 및 직장인을 위한 합격 정보
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 mb-4">
          {/* 비전공자 합격률 */}
          {feasibilityInfo.non_major_pass_rate && (
            <div className="bg-emerald-900/10 rounded-lg p-3 border border-emerald-500/20">
              <div className="flex items-center gap-1.5 mb-1">
                <Users className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                <span className="text-xs text-muted-foreground">비전공자 합격률</span>
              </div>
              <span className="text-base font-bold text-emerald-400">
                {feasibilityInfo.non_major_pass_rate}
              </span>
            </div>
          )}

          {/* 1회 응시 합격률 */}
          {feasibilityInfo.first_attempt_pass_rate && (
            <div className="bg-cyan-900/10 rounded-lg p-3 border border-cyan-500/20">
              <div className="flex items-center gap-1.5 mb-1">
                <TrendingUp className="h-3.5 w-3.5 text-cyan-400 flex-shrink-0" />
                <span className="text-xs text-muted-foreground">1회 합격률</span>
              </div>
              <span className="text-base font-bold text-cyan-400">
                {feasibilityInfo.first_attempt_pass_rate}
              </span>
            </div>
          )}

          {/* 독학 가능 여부 */}
          {feasibilityInfo.self_study_possible !== null && (
            <div
              className={cn(
                'rounded-lg p-3 border',
                feasibilityInfo.self_study_possible
                  ? 'bg-emerald-900/10 border-emerald-500/20'
                  : 'bg-amber-900/10 border-amber-500/20'
              )}
            >
              <div className="flex items-center gap-1.5 mb-1">
                {feasibilityInfo.self_study_possible ? (
                  <CheckCircle className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                ) : (
                  <XCircle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" />
                )}
                <span className="text-xs text-muted-foreground">독학 가능</span>
              </div>
              <span
                className={cn(
                  'text-base font-bold',
                  feasibilityInfo.self_study_possible ? 'text-emerald-400' : 'text-amber-400'
                )}
              >
                {feasibilityInfo.self_study_possible ? '가능' : '인강 권장'}
              </span>
            </div>
          )}

          {/* 최소 준비 기간 */}
          {feasibilityInfo.minimum_study_period !== null && (
            <div className="bg-violet-900/10 rounded-lg p-3 border border-violet-500/20">
              <div className="flex items-center gap-1.5 mb-1">
                <Clock className="h-3.5 w-3.5 text-violet-400 flex-shrink-0" />
                <span className="text-xs text-muted-foreground">최소 준비 기간</span>
              </div>
              <span className="text-base font-bold text-violet-400">
                {feasibilityInfo.minimum_study_period >= 30
                  ? `약 ${Math.max(1, Math.round(feasibilityInfo.minimum_study_period / 30))}개월`
                  : `${feasibilityInfo.minimum_study_period}일`}
              </span>
            </div>
          )}
        </div>

        {/* 직장인 팁 */}
        {(feasibilityInfo.working_adult_tips?.length ?? 0) > 0 && (
          <div className="mt-4 pt-4 border-t border-border">
            <div className="flex items-center gap-2 mb-3">
              <Briefcase className="h-4 w-4 text-amber-400" />
              <span className="text-sm font-medium text-amber-400">직장인 학습 팁</span>
            </div>
            <ul className="space-y-2">
              {feasibilityInfo.working_adult_tips.map((tip, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <span className="text-amber-400 mt-0.5">•</span>
                  <span className="text-foreground/80">{tip}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
