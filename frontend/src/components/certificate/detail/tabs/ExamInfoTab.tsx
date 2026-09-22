'use client'

import {
  Target,
  DollarSign,
  FileText,
  Info,
  ExternalLink,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ExamScheduleCard } from '../ExamScheduleCard'
import {
  type Certificate,
  hasExamInfo,
  hasExamScheduleDetail,
  hasOfficialSources,
  isExamSubject,
} from '@/lib/api/types'

interface ExamInfoTabProps {
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

function formatFee(fee: string | null | undefined): string {
  if (!fee) return ''
  const feeStr = fee.toString().trim()
  const normalized = feeStr.endsWith('원') ? feeStr.slice(0, -1).trim() : feeStr
  const numericCandidate = normalized.replace(/,/g, '')
  const isNumeric = numericCandidate.length > 0 && !isNaN(Number(numericCandidate))
  if (!isNumeric) return feeStr
  const formatted = Number(numericCandidate).toLocaleString()
  return numericCandidate.endsWith('0') ? `${formatted}원` : formatted
}

/**
 * ExamInfoTab - 시험 정보 탭
 *
 * 시험 과목, 형식, 일정, 응시료 등을 표시합니다.
 */
export function ExamInfoTab({ certificate }: ExamInfoTabProps) {
  const cert = certificate
  const hasExam = hasExamInfo(cert)
  const hasSchedule = hasExamScheduleDetail(cert)
  const hasSources = hasOfficialSources(cert)

  if (!hasExam && !hasSchedule) {
    return (
      <Card className="bg-card/50 border-border">
        <CardContent className="py-8">
          <NoDataMessage message="시험 정보가 아직 등록되지 않았습니다" />
          {hasSources && cert.official_sources.official_site && (
            <div className="text-center mt-4">
              <a
                href={cert.official_sources.official_site}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="outline" className="border-cyan-500/30 text-cyan-400">
                  공식 사이트에서 확인
                  <ExternalLink className="ml-2 h-4 w-4" />
                </Button>
              </a>
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* 시험 일정 카드 */}
      {hasSchedule && (
        <ExamScheduleCard scheduleDetail={cert.exam_schedule_detail!} />
      )}

      {/* 시험 과목 */}
      {hasExam && cert.exam_info.subjects.length > 0 && (
        <Card className="bg-card/50 border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-emerald-400" />
              시험 과목
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-4">
              {cert.exam_info.subjects.map((subject, index) => (
                <li key={index}>
                  {isExamSubject(subject) ? (
                    /* 새 형식: {name, details, topics} 객체 */
                    <div className="bg-muted/30 p-4 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-foreground">{subject.name}</span>
                        {subject.details && (
                          <span className="text-sm text-muted-foreground">{subject.details}</span>
                        )}
                      </div>
                      {subject.topics && subject.topics.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2">
                          {subject.topics.map((topic, topicIndex) => (
                            <span
                              key={topicIndex}
                              className="text-sm bg-emerald-900/30 text-emerald-400 px-2 py-1 rounded"
                            >
                              {topic}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    /* 기존 형식: 문자열 */
                    <div className="flex items-start gap-2 bg-muted/30 p-3 rounded-lg">
                      <span className="text-emerald-400 mt-1">•</span>
                      <span className="text-foreground/80">{subject}</span>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* 시험 형식 & 합격 기준 */}
      {hasExam && (
        <div className="grid md:grid-cols-2 gap-6">
          {cert.exam_info.exam_type && (
            <Card className="bg-card/50 border-border">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <FileText className="h-5 w-5 text-cyan-400" />
                  시험 형식
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-foreground/80">{cert.exam_info.exam_type}</p>
              </CardContent>
            </Card>
          )}

          {cert.exam_info.passing_criteria && (
            <Card className="bg-card/50 border-border">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Target className="h-5 w-5 text-violet-400" />
                  합격 기준
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-foreground/80">{cert.exam_info.passing_criteria}</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* 응시료 */}
      {hasExam && cert.exam_info.total_fee && (
        <Card className="bg-card/50 border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-amber-400" />
              응시료
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between p-4 bg-amber-900/10 rounded-lg border border-amber-500/20">
              <span className="text-foreground/80">총 응시료</span>
              <span className="text-2xl font-bold text-amber-400">
                {formatFee(cert.exam_info.total_fee)}
              </span>
            </div>
            {cert.cost_breakdown?.exam_fee_refund && (
              <p className="text-xs text-muted-foreground mt-2">
                환불 정책: {cert.cost_breakdown.exam_fee_refund}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* 공식 사이트 안내 */}
      {hasSources && cert.official_sources.official_site && (
        <Card className="bg-gradient-to-r from-cyan-900/20 to-emerald-900/20 border-cyan-500/20">
          <CardContent className="py-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex-1">
                <h3 className="font-semibold text-foreground mb-1">
                  📅 최신 시험 일정이 필요하신가요?
                </h3>
                <p className="text-sm text-foreground/80">
                  접수 기간, 시험일, 합격 발표일 등 정확한 정보는 공식 사이트에서 확인하세요.
                </p>
              </div>
              <a
                href={cert.official_sources.official_site}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button className="bg-gradient-to-r from-cyan-500 to-emerald-500 hover:from-cyan-600 hover:to-emerald-600 text-white">
                  공식 사이트
                  <ExternalLink className="ml-2 h-4 w-4" />
                </Button>
              </a>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
