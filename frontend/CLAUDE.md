# Frontend - Certificate Master

## Architecture Overview

### Framework & Core Technologies
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript 5.x
- **Styling**: Tailwind CSS + shadcn/ui
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Authentication**: ivetech 통합 인증 서비스(auth-service, JWT) — `NEXT_PUBLIC_AUTH_ENABLED`로 on/off
- **Forms**: React Hook Form + Zod validation

---

## Project Structure

```
frontend/
├── src/
│   ├── app/                        # App Router pages
│   │   ├── oauth/callback/         # auth-service OAuth2(Google) 콜백 (#access_token)
│   │   ├── login/                  # 로그인 (이메일 + Google, 인증 꺼짐 시 안내 화면)
│   │   ├── signup/                 # 회원가입 (인증 꺼짐 시 안내 화면)
│   │   ├── search/                 # 자격증 검색 페이지 (통합 검색 + AI 추천) ⭐UPDATED (2026-01-14)
│   │   ├── certificates/[id]/      # 자격증 상세 페이지
│   │   ├── dashboard/              # 학습 대시보드 (실시간 데이터) ⭐UPDATED (2026-01-07)
│   │   ├── study-plans/            # 학습 계획 페이지 ⭐NEW (2026-01-06)
│   │   │   ├── page.tsx            # 학습 계획 목록
│   │   │   └── [id]/page.tsx       # 학습 계획 상세
│   │   ├── layout.tsx              # 전역 레이아웃
│   │   ├── page.tsx                # 랜딩 페이지
│   │   └── globals.css             # 전역 스타일
│   ├── components/
│   │   ├── ui/                     # shadcn/ui 컴포넌트
│   │   ├── auth/                   # 인증 관련 컴포넌트
│   │   │   ├── login-form.tsx        # 이메일/비밀번호 + Google 로그인
│   │   │   ├── signup-form.tsx       # 회원가입 (auth-service 비밀번호 규칙)
│   │   │   ├── require-auth.tsx      # 보호 페이지 가드 (dashboard/study-plans/analytics layout)
│   │   │   └── index.ts
│   │   ├── providers/              # React Context Providers ⭐NEW
│   │   │   ├── session-provider.tsx # 세션 초기화
│   │   │   └── index.ts
│   │   ├── certificate/            # 자격증 관련 컴포넌트
│   │   │   ├── certificate-card.tsx
│   │   │   ├── search-filters.tsx
│   │   │   ├── search-input.tsx
│   │   │   └── index.ts
│   │   ├── recommend/              # AI 추천 관련 컴포넌트 ⭐NEW (2026-01-14)
│   │   │   ├── search-tabs.tsx             # 추천받기/직접검색 탭
│   │   │   ├── interaction-wizard.tsx      # 5단계 인터랙션 위자드
│   │   │   ├── wizard-progress.tsx         # 진행 상황 표시
│   │   │   ├── wizard-step.tsx             # 위자드 단계별 UI
│   │   │   ├── option-card.tsx             # 선택 가능한 옵션 카드
│   │   │   ├── time-slider.tsx             # 학습 시간 슬라이더
│   │   │   ├── recommendation-results.tsx  # 추천 결과 표시
│   │   │   ├── recommendation-card.tsx     # 추천 자격증 카드
│   │   │   └── index.ts
│   │   ├── dashboard/              # 대시보드 관련 컴포넌트
│   │   │   ├── progress-card.tsx
│   │   │   ├── today-tasks.tsx
│   │   │   ├── weekly-chart.tsx
│   │   │   ├── study-timeline.tsx
│   │   │   └── index.ts
│   │   ├── study-plan/            # 학습 계획 관련 컴포넌트 ⭐UPDATED (2026-01-07)
│   │   │   ├── study-plan-list.tsx           # 학습 계획 목록
│   │   │   ├── create-study-plan-form.tsx    # 학습 계획 생성 폼
│   │   │   ├── checkin-modal.tsx             # 체크인 모달 ⭐NEW (2026-01-07)
│   │   │   ├── ai-encouragement.tsx          # AI 응원 메시지 ⭐NEW (2026-01-07)
│   │   │   └── index.ts
│   │   └── layout/                 # 레이아웃 컴포넌트
│   │       ├── header.tsx
│   │       ├── footer.tsx
│   │       └── index.ts
│   ├── lib/
│   │   ├── api/                    # 백엔드 API 클라이언트 ✨NEW
│   │   │   ├── client.ts           # HTTP 클라이언트
│   │   │   ├── types.ts            # API 타입 정의
│   │   │   ├── certificates.ts     # 자격증 API
│   │   │   ├── recommendations.ts  # 자격증 추천 API ⭐NEW (2026-01-14)
│   │   │   ├── study-plans.ts      # 학습 계획 API
│   │   │   ├── checkins.ts         # 체크인 API
│   │   │   └── index.ts            # 통합 export
│   │   ├── auth/                   # ivetech auth-service 연동
│   │   │   ├── config.ts           # AUTH_ENABLED, AUTH_API_URL
│   │   │   ├── token-manager.ts    # access(메모리) / refresh(localStorage) 토큰
│   │   │   └── auth-api.ts         # login/signup/refresh/logout/Google URL
│   │   ├── providers.tsx           # TanStack Query Provider
│   │   └── utils.ts                # 유틸리티 함수
│   ├── hooks/                      # 커스텀 훅 ⭐UPDATED (2026-01-14)
│   │   ├── use-certificates.ts     # 자격증 데이터 훅
│   │   ├── use-recommendations.ts  # 자격증 추천 훅 ⭐NEW (2026-01-14)
│   │   ├── use-study-plans.ts      # 학습 계획 훅
│   │   ├── use-checkins.ts         # 체크인 훅 ⭐NEW (2026-01-07)
│   │   ├── use-auth.ts             # 인증 상태 관리 훅
│   │   ├── use-debounce.ts         # 디바운스 훅
│   │   └── index.ts                # 통합 export
│   ├── stores/
│   │   ├── auth-store.ts           # 인증 상태 관리
│   │   ├── search-store.ts         # 검색 상태 관리
│   │   └── recommend-store.ts      # 추천 위자드 상태 관리 ⭐NEW (2026-01-14)
│   ├── types/
│   │   ├── database.types.ts       # DB 스키마 타입 (과거 Supabase CLI로 생성)
│   │   └── index.ts                # 공통 타입
├── tests/                          # E2E 테스트 ⭐UPDATED (2026-01-14)
│   └── e2e/
│       ├── landing.spec.ts         # 랜딩 페이지 테스트
│       ├── search.spec.ts          # 검색 페이지 테스트
│       ├── recommend.spec.ts       # AI 추천 위자드 테스트 ⭐NEW (2026-01-14)
│       ├── certificate-detail.spec.ts
│       ├── auth.spec.ts            # 인증 테스트 (Email/Password - Deprecated)
│       ├── google-auth.spec.ts     # Google OAuth 테스트
│       ├── session-management.spec.ts # 세션 관리 테스트
│       ├── study-plans.spec.ts     # 학습 계획 테스트
│       ├── dashboard.spec.ts       # 대시보드 테스트 ⭐UPDATED (2026-01-07)
│       ├── checkin.spec.ts         # 체크인 기능 테스트 ⭐NEW (2026-01-07)
│       └── navigation.spec.ts      # 네비게이션 테스트
├── public/
├── .env.example
├── .env.local                      # 로컬 환경 변수 (Git 무시)
├── playwright.config.ts            # Playwright 설정 ✨NEW
├── next.config.js
├── tailwind.config.ts
└── package.json
```

---

## Development Status

### ✅ Completed Features

1. **프로젝트 초기화**
   - Next.js 14 + TypeScript + Tailwind CSS
   - shadcn/ui 컴포넌트 라이브러리 설정

2. **검색 기능 개선 (2026-01-06)** ⭐ NEW
   - ✅ 실시간 검색 자동완성 (Autocomplete)
     - API 기반 자격증 제목 제안
     - 300ms Debounce 적용
     - 카테고리 및 계열 정보 함께 표시
   - ✅ 계층 구조 필터 (Category > Series)
     - 2단계 필터링: 자격구분 → 계열
     - 동적 로딩 및 자동 초기화
     - 시각적 계층 표현
   - ✅ 무한 스크롤 (Infinite Scroll)
     - React Query useInfiniteQuery
     - Intersection Observer API
     - 페이지당 20개 항목 로드
   - 🗑️ 인기 검색어 기능 제거 (Mock 데이터 대체)
   - Supabase 클라이언트 및 미들웨어 설정

2. **레이아웃**
   - Header (네비게이션, 로그인/로그아웃)
   - Footer (링크, 소셜)
   - 반응형 디자인 (모바일 메뉴 포함)

3. **랜딩 페이지**
   - 히어로 섹션 (그라디언트 배경, CTA 버튼)
   - 주요 기능 3개 소개 카드
   - 통계 섹션
   - 인기 자격증 캐러셀
   - CTA 섹션

4. **검색 페이지**
   - 자동완성 검색 입력
   - 필터 (난이도, 분야, 준비기간)
   - 검색 결과 카드 그리드
   - 그리드/리스트 뷰 전환
   - 관심 등록 (하트) 기능

5. **자격증 상세 페이지**
   - 탭 메뉴 (개요, 학습계획, 추천 강의, 시험정보)
   - 난이도/합격률/준비기간 표시
   - 학습 일정 타임라인
   - 추천 강의 목록
   - 시험 정보 카드

6. **인증 & 세션 관리** ⭐ UPDATED (2026-01-06)
   - ✅ **Google OAuth 소셜 로그인** (단일 인증 방식)
     - Google 계정 원클릭 로그인
     - OAuth 2.0 Authorization Code Flow
     - 자동 세션 관리 및 쿠키 저장
   - ✅ **useAuth Hook** (세션 관리)
     - 앱 로드 시 자동 세션 체크
     - 실시간 auth 상태 변경 감지
     - isAuthenticated, isLoading, user, signOut
   - ✅ **SessionProvider** (전역 세션 동기화)
     - Supabase 세션 ↔ Zustand store 동기화
     - onAuthStateChange 이벤트 처리
   - ✅ **로그아웃 기능**
     - Header에서 signOut() 호출
     - 세션 종료 + Store 클리어 + 홈 리다이렉션
   - ✅ **에러 처리**
     - 로그인 실패 시 에러 메시지 표시
     - 네트워크 에러 시 로컬 로그아웃
   - 🗑️ 이메일/비밀번호 로그인 제거
   - 🗑️ 회원가입 페이지 제거 (→ /login 리다이렉션)
   - ✅ Protected Routes 미들웨어

7. **학습 대시보드** ⭐UPDATED (2026-01-06)
   - ✅ 실시간 API 데이터 연동
   - ✅ 통계 카드 (진행 중/완료/진행률/예정 시간)
   - ✅ 진행 중인 학습 계획 목록
   - ✅ Empty State (학습 계획 없을 때)
   - ✅ 로딩 및 에러 상태 처리

8. **학습 계획 관리** ✨NEW (2026-01-06)
   - ✅ 학습 계획 생성 폼 (Dialog)
     - 자격증 선택 (자격증 상세 페이지에서)
     - 목표 날짜 설정
     - 하루 학습 시간 설정 (0.5~12시간)
     - 자동 마일스톤 생성
   - ✅ 학습 계획 목록 페이지
     - 진행률 표시
     - 상태 Badge (진행 중/일시 중지/완료/취소)
     - 마일스톤 미리보기
     - 삭제 기능
   - ✅ 학습 계획 상세 페이지
     - 통계 카드 (진행률/남은 기간/하루 학습/총 시간)
     - 마일스톤 체크리스트
     - 상태 변경 (일시 중지/재개/완료)
     - 삭제 확인 다이얼로그

9. **백엔드 API 연동** ⭐UPDATED (2026-01-06)
   - ✅ HTTP 클라이언트 구현 (에러 처리 포함)
   - ✅ **Supabase JWT 토큰 인증 추가** ⭐NEW
   - ✅ API 타입 정의 (Certificate, StudyPlan, Checkin)
   - ✅ React Query hooks (useCertificates, useStudyPlans)
   - ✅ **Study Plan CRUD hooks** (생성/조회/수정/삭제) ⭐NEW
   - ✅ 검색 페이지 API 연동
   - ✅ 상세 페이지 API 연동
   - ✅ Dashboard API 연동 (실시간 데이터) ⭐NEW
   - ✅ 자동 캐싱 및 재검증

10. **AI 추천 위자드 (RAG 기반)** ⭐NEW (2026-01-14)
   - ✅ **5단계 인터랙션 위자드**
     - Step 1: 분야 선택 (8개 데이터 기반 카테고리, 아이콘 포함)
     - Step 2: 목표 선택 (취업/이직/승진/자기계발/창업)
     - Step 3: 경험 수준 (처음/전공/실무/하위자격증)
     - Step 4: 하루 학습 시간 (슬라이더, 0.5~6시간)
     - Step 5: 목표 기간 (1개월/3개월/6개월/1년/정하지 않음)
   - ✅ **검색 페이지 통합**
     - 추천받기/직접 검색 탭 전환
     - 탭별 독립적인 상태 관리
     - 추천 결과 표시 (match_score, key_points, feasibility)
     - 다시 추천받기 기능
   - ✅ **Zustand 상태 관리**
     - 위자드 진행 상태 (currentStep, answers)
     - 추천 결과 상태 (recommendations, querySummary)
     - 전진/후진 네비게이션
     - 답변 검증 (areAllAnswersComplete)
   - ✅ **컴포넌트 구조**
     - InteractionWizard (메인 컨테이너)
     - WizardProgress (진행 상황)
     - WizardStep (단계별 UI - options/slider 타입 지원)
     - OptionCard (선택 옵션, 아이콘 지원)
     - TimeSlider (학습 시간 슬라이더)
     - RecommendationResults (추천 결과)
     - RecommendationCard (개별 추천 카드)

11. **E2E 테스트 (Playwright)** ⭐UPDATED (2026-01-14)
   - **AI 추천 위자드 테스트 추가** ⭐NEW (17개 테스트)
     - ✅ 탭 전환 테스트 (3개)
     - ✅ Step 1: 분야 선택 (3개)
     - ✅ Step 2: 목표 선택 (2개)
     - ✅ Step 3: 경험 수준 (1개)
     - ✅ Step 4: 학습 시간 슬라이더 (2개)
     - ✅ Step 5: 목표 기간 (2개)
     - ⚠️  추천 결과 테스트 (4개 - 백엔드 API 필요)
   - **학습 계획 테스트** (12개)
     - ✅ Empty State 테스트
     - ✅ 학습 계획 생성 플로우
     - ✅ 학습 계획 목록 표시
     - ✅ 상세 페이지 표시
     - ✅ 마일스톤 완료 처리
     - ✅ 상태 변경 (일시 중지/재개)
     - ✅ 삭제 기능
     - ✅ Dashboard 통합 테스트
     - ✅ 인증 필요 테스트
     - ✅ 폼 유효성 검사
     - ✅ API 에러 처리
   - **총 135+ 테스트** (기존 103개 + AI 추천 17개 + 기타 15개)
   - **통과율**: 12/17 passing (71%) - 4개 테스트는 백엔드 API 연동 필요
   - 실제 API 데이터 사용
   - 랜딩/검색/추천/상세/인증/대시보드/학습 계획 페이지
   - Chromium 브라우저 테스트
   - CI/CD 준비 완료

12. **Backend Schema V2 연동** ✨NEW (2026-01-06)
   - TypeScript 타입 정의 완전히 업데이트
   - 6개 탭 구조로 정보 분류 (개요/시험/일정/진로/강의/후기)
   - 공식 일정 링크, 응시 자격, 진로 정보, 후기 섹션 추가
   - 강의 평점 및 관련성 점수 표시
   - 공식 출처 명시로 신뢰성 향상
   - 타입 가드 함수로 안전한 데이터 접근

---

## Running the Development Server

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local
cp .env.example .env.local
# Edit .env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Run development server
npm run dev
```

The app will be available at http://localhost:3000 (or 3001 if 3000 is in use)

---

## Key Dependencies

```json
{
  "dependencies": {
    "next": "14.x",
    "react": "18.x",
    "@supabase/supabase-js": "^2.x",
    "@supabase/ssr": "^0.x",
    "@tanstack/react-query": "^5.x",
    "@tanstack/react-query-devtools": "^5.x",
    "zustand": "^5.x",
    "react-hook-form": "^7.x",
    "zod": "^4.x",
    "@hookform/resolvers": "^5.x",
    "lucide-react": "latest",
    "class-variance-authority": "latest",
    "clsx": "latest",
    "tailwind-merge": "latest"
  },
  "devDependencies": {
    "@playwright/test": "^1.57.0",
    "typescript": "^5.x",
    "tailwindcss": "^3.x"
  }
}
```

---

## Design System

### Colors
- **Primary**: Emerald (emerald-400 to emerald-600)
- **Accent**: Cyan (cyan-400 to cyan-600)
- **Background**: Slate (slate-900 to slate-950)
- **Text**: White / Slate-300 / Slate-400 / Slate-500

### Typography
- **Font**: Outfit (Google Fonts)
- **Headings**: Bold (700-800)
- **Body**: Regular (400-500)

### Components
- Glass effect: `bg-slate-900/50 backdrop-blur-xl border border-slate-800/50`
- Card hover: `hover:shadow-xl hover:shadow-emerald-500/10 hover:-translate-y-1`
- Gradient text: `bg-gradient-to-r from-emerald-400 via-cyan-400 to-emerald-400 bg-clip-text text-transparent`

---

## TODO (Next Steps)

### API Integration
- [x] Connect to backend API endpoints ✅
- [x] Implement certificate search with real data ✅
- [x] React Query hooks for data fetching ✅
- [x] Autocomplete API integration ✅ (2026-01-06)
- [x] Series by category API integration ✅ (2026-01-06)
- [x] Infinite scroll with pagination ✅ (2026-01-06)
- [x] **Supabase JWT 인증 추가** ✅ (2026-01-06) ⭐NEW
- [x] **Study plan CRUD operations** ✅ (2026-01-06) ⭐NEW
- [x] **RAG Recommendation Frontend** ✅ (2026-01-14) ⭐NEW
  - [x] 5단계 인터랙션 위자드 UI
  - [x] Zustand 상태 관리
  - [x] React Query mutation
  - [ ] Backend API 연동 (4개 E2E 테스트 대기)
- [ ] Implement check-in functionality (UI integration)
- [x] User authentication flow (Supabase Auth) ✅

### Features
- [x] Supabase local development setup documentation ✅
- [x] Search autocomplete ✅ (2026-01-06)
- [x] Hierarchical filters (category > series) ✅ (2026-01-06)
- [x] Infinite scroll ✅ (2026-01-06)
- [x] **Study plan creation modal** ✅ (2026-01-06) ⭐NEW
- [x] **Study plan list & detail pages** ✅ (2026-01-06) ⭐NEW
- [x] **Dashboard with real study plan data** ✅ (2026-01-06) ⭐NEW
- [ ] User profile page
- [ ] Community/forum section
- [ ] Push notifications
- [ ] Dark/Light mode toggle

### Testing
- [x] E2E testing setup (Playwright) ✅
- [x] Landing page tests ✅
- [x] Search & certificate detail tests ✅
- [x] Authentication UI tests ✅
- [x] **Google OAuth tests** ✅ (2026-01-06 ⭐NEW)
- [x] **Session management tests** ✅ (2026-01-06 ⭐NEW)
- [x] Dashboard tests ✅
- [x] Responsive design tests ✅
- [ ] Infinite scroll E2E tests (needs update)
- [ ] Autocomplete E2E tests (needs addition)
- [ ] Hierarchical filter E2E tests (needs addition)
- [ ] API integration tests
- [ ] Unit tests for hooks
- [ ] Visual regression tests

**Latest Test Results (2026-01-06)**:
- Total: 123 tests (93 existing + 14 Google OAuth + 16 session management)
- Passed: 116+ ✓ (~94%)
- Google OAuth: **14/14 passed** ✅ (100%)
- Session Management: **23/31 passed** ✅ (74%, 8 tests need real login)

**Recent Test Additions**:
- ✅ Search query reset via X button
- ✅ Search query reset via filter reset button
- ✅ Google OAuth login button (2026-01-06 ⭐NEW)
- ✅ Email/password form removal verification
- ✅ Signup page redirection
- ✅ OAuth flow initiation
- ✅ Protected routes with Google auth
- ✅ Responsive design (mobile/tablet)
- ✅ **Session initialization** (2026-01-06 ⭐NEW)
- ✅ **Login state check** (2026-01-06 ⭐NEW)
- ✅ **Logout functionality** (2026-01-06 ⭐NEW)
- ✅ **Error handling (auth)** (2026-01-06 ⭐NEW)

### DevOps
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Vercel deployment configuration
- [ ] Environment variable management
- [ ] Performance monitoring (Web Vitals)

---

## API Integration Architecture

### HTTP Client (`lib/api/client.ts`)
```typescript
// Centralized API client with error handling
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export class APIError extends Error {
  constructor(message: string, public status: number, public data?: any)
}

export const api = {
  get: <T>(endpoint: string) => fetchAPI<T>(endpoint, { method: 'GET' }),
  post: <T>(endpoint: string, data: any) => fetchAPI<T>(endpoint, { method: 'POST', body: JSON.stringify(data) }),
  patch: <T>(endpoint: string, data: any) => fetchAPI<T>(endpoint, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: <T>(endpoint: string) => fetchAPI<T>(endpoint, { method: 'DELETE' }),
}
```

### React Query Hooks
```typescript
// Example: useCertificates hook (single page)
import { useQuery } from '@tanstack/react-query'
import { certificatesAPI } from '@/lib/api'

export function useCertificates(params: SearchParams) {
  return useQuery({
    queryKey: ['certificates', 'list', params],
    queryFn: () => certificatesAPI.search(params),
    staleTime: 5 * 60 * 1000,  // 5 minutes
  })
}

// Example: useInfiniteCertificates hook (infinite scroll) ⭐ NEW
import { useInfiniteQuery } from '@tanstack/react-query'

export function useInfiniteCertificates(params: Omit<SearchParams, 'page'>) {
  return useInfiniteQuery({
    queryKey: ['certificates', 'infinite-list', params],
    queryFn: ({ pageParam = 1 }) => certificatesAPI.search({ ...params, page: pageParam }),
    getNextPageParam: (lastPage) => lastPage.has_more ? lastPage.page + 1 : undefined,
    initialPageParam: 1,
    staleTime: 5 * 60 * 1000,
  })
}
```

### Usage in Components
```typescript
// Example 1: Single page search (deprecated, use infinite scroll)
'use client'

import { useCertificates } from '@/hooks'

export default function SearchPageOld() {
  const { data, isLoading, error } = useCertificates({ q: 'IT', page: 1 })
  
  if (isLoading) return <Loader />
  if (error) return <ErrorFallback />
  
  return <CertificateGrid certificates={data?.items || []} />
}

// Example 2: Infinite scroll search ⭐ NEW (Current Implementation)
'use client'

import { useInfiniteCertificates } from '@/hooks'
import { useEffect, useRef } from 'react'

export default function SearchPage() {
  const { data, isLoading, error, fetchNextPage, hasNextPage, isFetchingNextPage } = 
    useInfiniteCertificates({ q: 'IT' })
  
  const observerTarget = useRef<HTMLDivElement>(null)
  
  // Intersection Observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage()
        }
      },
      { threshold: 0.1 }
    )
    if (observerTarget.current) observer.observe(observerTarget.current)
    return () => observer.disconnect()
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])
  
  // Flatten all pages
  const results = data?.pages.flatMap((page) => page.items) || []
  
  if (isLoading) return <Loader />
  if (error) return <ErrorFallback />
  
  return (
    <>
      <CertificateGrid certificates={results} />
      <div ref={observerTarget} />
      {isFetchingNextPage && <Loader />}
    </>
  )
}

// Example 3: Autocomplete ⭐ NEW
'use client'

import { useState, useEffect } from 'react'
import { certificatesAPI } from '@/lib/api'

export function SearchInput() {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState([])
  
  useEffect(() => {
    if (query.length < 1) return
    
    const timer = setTimeout(async () => {
      const results = await certificatesAPI.autocomplete(query, 10)
      setSuggestions(results)
    }, 300) // Debounce
    
    return () => clearTimeout(timer)
  }, [query])
  
  return (
    <div>
      <input value={query} onChange={(e) => setQuery(e.target.value)} />
      {suggestions.map(s => <div key={s.id}>{s.title}</div>)}
    </div>
  )
}
```

### Automatic Fallback
- API 오류 시 자동으로 Mock 데이터 표시
- 사용자에게 "API 오류" 배너 표시
- 개발 중에도 UI 테스트 가능

---

## Testing Guide

### Running Tests

```bash
# All tests (headless)
npm test

# UI mode (interactive)
npm run test:ui

# Headed mode (watch browser)
npm run test:headed

# Debug mode
npm run test:debug

# Generate HTML report
npm run test:report
```

### Test Structure
```typescript
// tests/e2e/search.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Search Page', () => {
  test('should display search results', async ({ page }) => {
    await page.goto('/search')
    await page.getByPlaceholder('자격증명 입력').fill('정보처리')
    await expect(page.getByText('정보처리기사')).toBeVisible()
  })
})
```

### Coverage
- **91 tests** across 6 test files
- Landing, Search, Detail, Auth, Dashboard, Navigation
- Responsive design tests (6 viewports)
- Accessibility tests
- **Latest Results (2026-01-06)**: 77/91 passing (84.6%) ⚠️
  - 14 tests need updating due to recent UI changes

---

## Environment Variables

### Required
```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Authentication (ivetech auth-service)
```bash
# 백엔드 AUTH_ENABLED 와 함께 켜고 끔 (기본 false)
NEXT_PUBLIC_AUTH_ENABLED=false
# dev: https://dev-auth.ivetech.co.kr / prod: https://auth.ivetech.co.kr
NEXT_PUBLIC_AUTH_API_URL=https://dev-auth.ivetech.co.kr
```

### Setup
```bash
# Create .env.local from example
cp .env.example .env.local

# Edit .env.local with your values
# Backend must be running on port 8000
```

---

## Best Practices

### Code Organization
1. **Use Server Components by default**: Only use `'use client'` when needed
2. **Implement Row Level Security**: Enable RLS policies in Supabase
3. **Type everything**: Use TypeScript strictly, avoid `any`
4. **Handle loading states**: Use Suspense boundaries and skeleton loaders
5. **Error boundaries**: Implement error.tsx for error handling

### API Integration
1. **Use React Query hooks**: Centralized data fetching with caching
2. **Implement fallbacks**: Mock data for development/testing
3. **Show error states**: User-friendly error messages
4. **Optimize requests**: Use `staleTime` and `cacheTime` appropriately
5. **Cancel requests**: Handle component unmounting

### Testing
1. **Write tests first (TDD)**: Test → Implement → Refactor
2. **Use specific locators**: `getByRole`, `getByLabel`, not CSS selectors
3. **Avoid timeouts**: Use `waitFor` and `expect` assertions
4. **Test user flows**: Not implementation details
5. **Keep tests fast**: Mock external dependencies

### Performance
1. **Code splitting**: Dynamic imports for large components
2. **Image optimization**: Use Next.js `<Image>` component
3. **Bundle analysis**: Run `npm run build` and check bundle size
4. **Lazy loading**: Use React.lazy() for non-critical components
5. **Memoization**: Use `useMemo` and `useCallback` judiciously

---

## Backend API Endpoints

### Certificate APIs

#### 1. Search Certificates
```
GET /api/v1/certificates/search
Query Parameters:
  - q: string (optional) - 검색 키워드
  - category: string (optional) - 자격구분명 필터
  - code: string (optional) - 자격구분코드 필터
  - page: integer (default: 1) - 페이지 번호
  - page_size: integer (default: 20) - 페이지 크기

Response:
{
  "items": Certificate[],
  "total": number,
  "page": number,
  "page_size": number,
  "has_more": boolean
}
```

#### 2. Autocomplete ⭐ NEW
```
GET /api/v1/certificates/autocomplete
Query Parameters:
  - q: string (required, min_length: 1) - 검색어
  - limit: integer (default: 10, max: 20) - 결과 개수

Response:
[
  {
    "id": "uuid",
    "title": "자격증명",
    "category": "자격구분",
    "series": "계열명" | null
  }
]
```

#### 3. Get Categories
```
GET /api/v1/certificates/categories

Response: string[] - 고유한 카테고리 목록
```

#### 4. Get Series by Category ⭐ NEW
```
GET /api/v1/certificates/series
Query Parameters:
  - category: string (optional) - 카테고리 필터

Response:
[
  {
    "category": "자격구분",
    "series": ["계열1", "계열2", ...]
  }
]
```

#### 5. Get Certificate by ID
```
GET /api/v1/certificates/{id}

Response: Certificate
```

### Study Plan APIs
```
GET    /api/v1/study-plans         - 학습 계획 목록
POST   /api/v1/study-plans         - 학습 계획 생성
GET    /api/v1/study-plans/{id}    - 학습 계획 상세
PATCH  /api/v1/study-plans/{id}    - 학습 계획 수정
DELETE /api/v1/study-plans/{id}    - 학습 계획 삭제
```

### Check-in APIs
```
GET  /api/v1/checkins              - 체크인 목록
POST /api/v1/checkins              - 체크인 생성
```

For detailed API documentation, see: `backend/SEARCH_API_GUIDE.md`

---

## Deployment

### Vercel (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables in Vercel dashboard
# NEXT_PUBLIC_API_URL=https://your-backend.com
```

### Build
```bash
npm run build
npm start
```

---

## Troubleshooting

### Issue: API Connection Failed
**Solution**: Check `NEXT_PUBLIC_API_URL` in `.env.local` and ensure backend is running

### Issue: CORS Error
**Solution**: Backend must allow frontend origin in `CORS_ORIGINS`

### Issue: Supabase Error
**Solution**: Not required if using backend API. Only needed for direct Supabase access

### Issue: Tests Failing
**Solution**: Run `npm run test:debug` to see detailed error messages

---

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [TanStack Query Guide](https://tanstack.com/query/latest)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [shadcn/ui Components](https://ui.shadcn.com/)

---

## 🚀 Performance Optimizations

### Debouncing (추가일: 2026-01-06)

모든 검색 파라미터에 300ms 디바운싱을 적용하여 불필요한 API 호출을 방지합니다.

**구현**:
```typescript
// Custom debounce hook
import { useDebounce } from '@/hooks/use-debounce'

// Apply debouncing to search parameters
const debouncedQuery = useDebounce(query, 300)
const debouncedCategory = useDebounce(filters.category, 300)
const debouncedSeries = useDebounce(filters.series, 300)
```

**적용 범위**:
- ✅ 검색어 입력
- ✅ 카테고리 필터 변경
- ✅ 계열 필터 변경
- ✅ 필터 초기화
- ✅ 검색어 삭제

**효과**:
- 📉 API 호출 횟수 감소
- ⚡ 빠른 입력 시 안정적인 동작
- 🎯 부드러운 사용자 경험
- 💰 네트워크 비용 절감

---

## 🔐 Authentication (ivetech 통합 인증 서비스)

> 2026-09: Supabase Auth → ivetech `auth-service`(ivetech-backend-service)로 전환.
> 아래 이전 기록(Supabase 기반 설명)은 더 이상 유효하지 않습니다.

### 동작 방식
- `NEXT_PUBLIC_AUTH_ENABLED=false`(기본): 로그인/회원가입 페이지는 "비활성화" 안내, 헤더 로그인 메뉴 없음, API 요청에 토큰 없음
- `true`: 아래 흐름 활성화 (백엔드도 `AUTH_ENABLED=true` + `JWT_SECRET` 필요)

### 흐름
```
이메일 로그인:  POST {AUTH_API_URL}/api/auth/login → { accessToken, refreshToken }
회원가입:       POST /api/auth/signup → 자동으로 login
Google:        {AUTH_API_URL}/oauth2/authorization/google?redirect_uri={origin}/oauth/callback
               → /oauth/callback#access_token=..&refresh_token=.. → 토큰 저장 후 주소창에서 제거
토큰 갱신:      POST /api/auth/refresh (refresh token rotation, 탭 간 Web Locks로 직렬화)
로그아웃:       POST /api/auth/logout (Bearer) → auth-service가 refresh token 폐기 + access token 블랙리스트
```

### 토큰 저장 (rasang 프론트엔드와 동일)
- access token: 메모리 (`lib/auth/token-manager.ts`)
- refresh token: localStorage `cm_refresh_token` (XSS 취약점 인지, httpOnly 쿠키 지원 시 교체)
- API 클라이언트(`lib/api/client.ts`)는 401 응답 시 refresh 후 1회 재시도

### 보호 페이지
- middleware 에서는 토큰을 볼 수 없어 `RequireAuth`(클라이언트 가드)를 `dashboard`/`study-plans`/`analytics` layout 에서 사용
- 실제 데이터 보호는 백엔드 JWT 검증이 담당

### auth-service 측 요구 설정
- CORS 허용: `https://dev-cert.i-ve.ai`, `https://cert.i-ve.ai`
- `oauth2.authorized-redirect-uris`: `https://{dev-}cert.i-ve.ai/oauth/callback`

---

**Last Updated**: 2026-01-14
**Status**: ✅ MVP Phase 1 Complete (Search + Auth + Study Plan CRUD + Dashboard + RAG Recommendation)

**Recent Updates (2026-01-14)**:

### RAG Recommendation System ⭐NEW
- ✨ **5단계 인터랙션 위자드 구현**
  - Step 1: 분야 선택 (8개 데이터 기반, 아이콘 지원)
  - Step 2-5: 목표/경험/시간/기간 선택
  - 자동 진행 (옵션 선택 시) + 수동 진행 (슬라이더)
- ✅ **검색 페이지에 탭 통합** (추천받기/직접 검색)
- ✅ **Zustand 상태 관리** (위자드 진행, 답변, 추천 결과)
- ✅ **React Query mutation** for API calls
- ✅ **17개 E2E 테스트** (12/17 passing - 4개 백엔드 API 필요)
- ✅ **필드명 업데이트**: `primary_interest` → `primary_field`, `user_status` → `experience_level`
- ✅ **8개 필드 매핑**: IT개발, 제조기술, 건설건축, 전문직, 사업서비스, 안전환경, 보건의료, 기타실무
- ✅ **4개 경험 수준**: 처음 시작, 관련 전공 있음, 실무 경험 있음, 하위 자격증 보유

**Previous Updates (2026-01-06)**:

### Authentication & Session Management
- 🔐 **Google OAuth** implemented as single auth method
- 🗑️ Removed email/password authentication
- ✅ **useAuth hook** for global authentication state
- ✅ **SessionProvider** for app-wide session sync
- ✅ Real-time auth state change detection
- ✅ 14/14 Google OAuth E2E tests passing
- ✅ 23/31 Session Management E2E tests passing (8 require real login)

### Study Plan Features ⭐UPDATED (2026-01-06)
- ✅ **Supabase JWT 인증 추가** (API 클라이언트)
- ✅ **학습 계획 생성 폼 컴포넌트** (Dialog 방식)
  - 목표 날짜 설정 (유효성 검사)
  - 하루 학습 시간 (0.5~12시간)
  - 자동 마일스톤 생성 (최대 12주)
  - 예상 학습량 표시
- ✅ **학습 계획 목록 페이지** (`/study-plans`)
  - 카드 형태 목록 표시
  - 진행률 및 마일스톤 미리보기
  - 상태 Badge 표시
  - 삭제 기능
- ✅ **학습 계획 상세 페이지** (`/study-plans/[id]`)
  - 통계 카드 (4개)
  - 마일스톤 체크리스트
  - 상태 변경 버튼
  - 삭제 확인 다이얼로그
- ✅ **Dashboard에 실시간 데이터 표시**
  - API 연동 (useStudyPlans)
  - 통계 카드 (진행 중/완료/진행률/예정 시간)
  - 진행 중인 학습 계획 목록
- ✅ **E2E 테스트 12개 작성**
- ✅ Login check before adding to study plan
- ✅ Auto-redirect to /login if not authenticated

### Type Safety & Bug Fixes
- 🐛 **Fixed TypeError** in type guards (optional chaining)
- ✅ All type guards now safely handle undefined arrays:
  - `hasExamInfo()`, `hasEligibility()`, `hasCareerInfo()`, `hasUserReviews()`
  - Uses `array?.length ?? 0` pattern

### Search & UX Features
- ✨ Added search debouncing (300ms)
- ✨ Added search autocomplete feature
- ✨ Added hierarchical filters (category > series)
- ✨ Implemented infinite scroll
- 🗑️ Removed trending searches (mock data)

### Dashboard Improvements ⭐UPDATED (2026-01-07)
- 🐛 **Fixed Data Display Issues** (TDD approach)
  - ✅ Certificate title display (was showing UUID)
  - ✅ Daily study hours display (field name correction: `daily_hours` → `daily_study_hours`)
  - ✅ NaN calculation error in total planned hours
- ✅ **Enhanced Dashboard Layout (2x2 Grid)** ⭐NEW
  - ✅ ProgressCard - 진행도, D-Day, 연속 학습일 표시
  - ✅ WeeklyChart - 주간 학습 시간 차트
  - ✅ TodayTasks - 오늘의 학습 + 체크인 버튼
  - ✅ StudyTimeline - 마일스톤 타임라인
- ✅ **"하루 학습" 제거** - 학습 계획 카드에서 제거
- ✅ **체크인 기능 보일러플레이팅** ⭐NEW
  - CheckinModal - 학습 시간/메모/기분 입력
  - AIEncouragement - 기분별 랜덤 응원 메시지
  - use-checkins.ts - React Query 훅 (CRUD + 통계)
- ✅ **All Tests Passing**: 17/17 dashboard tests + 5/5 checkin tests ✅

### Test Coverage ⭐UPDATED (2026-01-07)
- **Total Tests**: 165+ (기존 142+ 추가 테스트)
- **Dashboard Tests**: 17개 (13 existing + 4 new components) ⭐UPDATED
  - Display tests, Empty state, Navigation, ProgressCard, WeeklyChart, TodayTasks, StudyTimeline
- **Checkin Tests**: 5개 ⭐NEW
  - Button display, Modal open, Hours slider, Mood selector, Cancel close
- **Passing Rate**: 100% (22/22 관련 테스트)
- **E2E Tests**: Certificate detail, Google OAuth, Session management, Study plan CRUD, Dashboard, Checkin

---

**Next Steps**:
- ✅ ~~Study plan CRUD API integration~~ ✅ COMPLETED (2026-01-06)
- ✅ ~~Study plan dashboard UI~~ ✅ COMPLETED (2026-01-06)
- ✅ ~~Dashboard data display fixes~~ ✅ COMPLETED (2026-01-07)
- ✅ ~~Enhanced Dashboard (ProgressCard, TodayTasks, WeeklyChart, StudyTimeline)~~ ✅ COMPLETED (2026-01-07)
- ✅ ~~체크인 기능 보일러플레이팅~~ ✅ COMPLETED (2026-01-07)
- ✅ ~~RAG Recommendation Frontend~~ ✅ COMPLETED (2026-01-14)
- [ ] **RAG Recommendation Backend 연동** (백엔드 API 완성 후)
  - [ ] `/api/v1/recommendations/` 엔드포인트 테스트
  - [ ] E2E 테스트 4개 통과 확인
  - [ ] 추천 결과 UI 검증
  - [ ] 에러 핸들링 테스트
- [ ] 체크인 백엔드 API 테스트 및 연동 확인
- [ ] AI-generated study plans (LLM 통합)
- [ ] 학습 계획 수정 기능 (Edit form)
- [ ] 주간/월간 진행 차트
- [ ] 학습 통계 대시보드
