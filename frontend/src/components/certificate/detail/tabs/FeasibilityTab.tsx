'use client'

import {
  MessageSquare,
  Star,
  Lightbulb,
  AlertCircle,
  Calendar,
  Info,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { FeasibilityCard } from '../FeasibilityCard'
import { DifficultyBreakdown } from '../DifficultyBreakdown'
import {
  type Certificate,
  hasFeasibilityInfo,
  hasUserReviews,
  hasExtendedReviews,
  hasStudyGuide,
} from '@/lib/api/types'

interface FeasibilityTabProps {
  certificate: Certificate
}

function NoDataMessage({ message = '정보가 없습니다' }: { message?: string }) {
  return (
    <div className="flex items-center gap-2 text-muted-foreground py-8 justify-center">
      <Info className="h-5 w-5" />
      <span>{message}</span>
    </div>
  )
}

function SentenceSections({ text }: { text: string }) {
  const sentences = text
    .split(/\n+/)
    .flatMap((line) => line.split(/(?<=[.!?])\s+/))
    .map((sentence) => sentence.trim())
    .filter(Boolean)

  if (sentences.length === 0) return null

  return (
    <div className="space-y-3">
      {sentences.map((sentence, idx) => (
        <div key={`${sentence}-${idx}`} className="rounded-lg bg-muted/30 p-4">
          <p className="text-foreground/80 leading-relaxed">{sentence}</p>
        </div>
      ))}
    </div>
  )
}

/**
 * FeasibilityTab - 합격 전략 탭 (신규)
 *
 * 합격 가능성, 후기, 시험 당일 팁 등을 표시합니다.
 */
export function FeasibilityTab({ certificate }: FeasibilityTabProps) {
  const cert = certificate
  const hasFeasibility = hasFeasibilityInfo(cert)
  const hasReviews = hasUserReviews(cert)
  const hasExtended = hasExtendedReviews(cert)
  const hasGuide = hasStudyGuide(cert)

  const hasAnyData = hasFeasibility || hasReviews || hasExtended

  if (!hasAnyData) {
    return (
      <Card className="bg-card/50 border-border">
        <CardContent className="py-8">
          <NoDataMessage message="합격 전략 정보가 아직 등록되지 않았습니다" />
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* 합격 가능성 분석 */}
      {hasFeasibility && <FeasibilityCard feasibilityInfo={cert.feasibility_info!} />}

      {/* 난이도 분석 (확장된 난이도 정보가 있을 경우) */}
      {hasReviews && cert.user_reviews?.difficulty_breakdown && (
        <DifficultyBreakdown difficulty={cert.user_reviews.difficulty_breakdown} />
      )}

      {/* 준비기간 분포 */}
      {hasReviews && cert.user_reviews?.study_period_distribution && (
        <Card className="bg-card/50 border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calendar className="h-5 w-5 text-cyan-400" />
              합격자 준비기간 분포
            </CardTitle>
            <CardDescription>
              실제 합격자들이 준비한 기간 분포입니다
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(cert.user_reviews.study_period_distribution).map(
                ([period, percentage], idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-foreground/80">{period}</span>
                      <span className="text-cyan-400 font-medium">{percentage}</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyan-400 rounded-full transition-[width]"
                        style={{ width: percentage }}
                      />
                    </div>
                  </div>
                )
              )}
            </div>
            {cert.user_reviews.study_period_range_days && (
              <div className="mt-4 p-3 bg-muted/30 rounded-lg">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-xs text-muted-foreground">최소</p>
                    <p className="text-sm font-bold text-foreground/80">
                      {cert.user_reviews.study_period_range_days.min}일
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">평균</p>
                    <p className="text-sm font-bold text-cyan-400">
                      {cert.user_reviews.study_period_range_days.median}일
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">최대</p>
                    <p className="text-sm font-bold text-foreground/80">
                      {cert.user_reviews.study_period_range_days.max}일
                    </p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 합격자 후기 요약 */}
      {hasReviews && cert.user_reviews?.summary && (
        <Card className="bg-card/50 border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-emerald-400" />
              합격자 후기 요약
            </CardTitle>
          </CardHeader>
          <CardContent>
            <SentenceSections text={cert.user_reviews.summary} />
          </CardContent>
        </Card>
      )}

      {/* 난이도 평가 */}
      {hasReviews && cert.user_reviews?.difficulty_feedback && (
        <Card className="bg-card/50 border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Star className="h-5 w-5 text-amber-400" />
              난이도 평가
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-foreground/80 leading-relaxed">
              {cert.user_reviews.difficulty_feedback}
            </p>
          </CardContent>
        </Card>
      )}

      {/* 시험 당일 팁 */}
      {hasReviews && (cert.user_reviews?.exam_day_tips?.length ?? 0) > 0 && (
        <Card className="bg-card/50 border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-violet-400" />
              시험 당일 팁
            </CardTitle>
            <CardDescription>
              실제 응시자들이 공유한 시험 당일 조언
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {cert.user_reviews?.exam_day_tips?.map((tip, idx) => (
                <li
                  key={idx}
                  className="flex items-start gap-3 bg-violet-900/10 p-3 rounded-lg border border-violet-500/20"
                >
                  <span className="text-violet-400 font-bold">{idx + 1}.</span>
                  <span className="text-foreground/80">{tip}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* 공통 어려움 */}
      {hasReviews && (cert.user_reviews?.common_challenges?.length ?? 0) > 0 && (
        <Card className="bg-card/50 border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-amber-400" />
              공통 어려움
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {cert.user_reviews?.common_challenges.map((challenge, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-amber-400 mt-1">⚠️</span>
                  <span className="text-foreground/80">{challenge}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* 합격 팁 (학습 가이드에서) */}
      {hasGuide && (cert.study_guide?.success_tips?.length ?? 0) > 0 && (
        <Card className="bg-card/50 border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-yellow-400" />
              합격 핵심 팁
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {cert.study_guide?.success_tips.map((tip, idx) => (
                <li
                  key={idx}
                  className="flex items-start gap-3 bg-yellow-900/10 p-3 rounded-lg"
                >
                  <Lightbulb className="h-4 w-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                  <span className="text-foreground/80">{tip}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
