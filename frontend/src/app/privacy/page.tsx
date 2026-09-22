import { Metadata } from 'next'

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://cert.i-ve.ai'

export const metadata: Metadata = {
  title: '개인정보 처리방침',
  description: '자격증 마스터의 개인정보 처리방침입니다. 수집하는 정보와 이용 목적을 안내합니다.',
  openGraph: {
    title: '개인정보 처리방침 | 자격증 마스터',
    description: '자격증 마스터의 개인정보 처리방침입니다.',
    type: 'website',
    locale: 'ko_KR',
    siteName: '자격증 마스터',
    url: `${SITE_URL}/privacy`,
  },
  alternates: {
    canonical: `${SITE_URL}/privacy`,
  },
  robots: {
    index: true,
    follow: false,
  },
}

export default function PrivacyPage() {
  return (
    <div className="container mx-auto px-4 py-12 max-w-3xl">
      <h1 className="text-3xl font-bold mb-8">개인정보 처리방침</h1>
      <p className="text-sm text-muted-foreground mb-8">
        최종 수정일: 2026년 2월 19일
      </p>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">1. 수집하는 개인정보</h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          자격증 마스터는 서비스 제공을 위해 다음과 같은 정보를 수집합니다:
        </p>
        <ul className="list-disc list-inside text-muted-foreground space-y-2">
          <li>Google OAuth 로그인을 통해 수집되는 이메일 주소, 프로필 이미지</li>
          <li>서비스 이용 기록 (학습 계획, 체크인 내역)</li>
          <li>접속 로그 (IP 주소, 브라우저 정보 — Google Analytics 수집)</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">2. 개인정보 이용 목적</h2>
        <ul className="list-disc list-inside text-muted-foreground space-y-2">
          <li>회원 식별 및 서비스 제공</li>
          <li>맞춤형 학습 계획 생성 및 관리</li>
          <li>서비스 개선을 위한 통계 분석 (Google Analytics 4 활용)</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">3. 제3자 서비스</h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          서비스는 다음 제3자 서비스를 이용합니다:
        </p>
        <ul className="list-disc list-inside text-muted-foreground space-y-2">
          <li>
            <strong>Google OAuth</strong> — 로그인 인증.{' '}
            <a href="https://policies.google.com/privacy" className="text-primary underline" target="_blank" rel="noopener noreferrer">Google 개인정보처리방침</a>
          </li>
          <li>
            <strong>Google Analytics 4</strong> — 방문자 통계 분석.{' '}
            <a href="https://policies.google.com/technologies/partner-sites" className="text-primary underline" target="_blank" rel="noopener noreferrer">Google의 데이터 이용방침</a>
          </li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">4. 개인정보 보유 기간</h2>
        <p className="text-muted-foreground leading-relaxed">
          회원 탈퇴 시 즉시 삭제합니다. 단, 관계 법령에 따라 보존이 필요한 경우 해당 기간 동안 보유합니다.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">5. 개인정보 삭제 요청</h2>
        <p className="text-muted-foreground leading-relaxed">
          개인정보 삭제 및 열람을 요청하시려면 아래 이메일로 문의해 주세요.
        </p>
        <p className="mt-2 text-foreground font-medium">이메일: contact@i-ve.ai</p>
      </section>
    </div>
  )
}
