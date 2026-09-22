/**
 * 인증 설정 (빌드 타임 고정 값)
 *
 * NEXT_PUBLIC_AUTH_ENABLED=true 일 때만 로그인/회원가입 화면과 보호 페이지 가드가 동작합니다.
 * 기본값(false)은 제한 공개 기간의 기존 동작(로그인 비활성화)을 유지합니다.
 * 백엔드의 AUTH_ENABLED 와 함께 켜고 꺼야 합니다.
 */
export const AUTH_ENABLED = process.env.NEXT_PUBLIC_AUTH_ENABLED === 'true'

/** ivetech 통합 인증 서비스 주소 (예: https://dev-auth.ivetech.co.kr) */
export const AUTH_API_URL = (process.env.NEXT_PUBLIC_AUTH_API_URL || '').replace(/\/+$/, '')

/** auth-service OAuth2 로그인 완료 후 돌아올 경로 (auth-service 허용 목록에 등록되어 있어야 함) */
export const OAUTH_CALLBACK_PATH = '/oauth/callback'

/** 로그인 후 돌아갈 경로를 OAuth 왕복 동안 보관하는 sessionStorage 키 */
export const POST_LOGIN_REDIRECT_KEY = 'cm_post_login_redirect'

/** 외부 URL로의 이동을 막기 위해 같은 사이트 내부 경로만 허용 */
export function sanitizeRedirectPath(path: string | null | undefined): string {
  if (!path || !path.startsWith('/') || path.startsWith('//') || path.startsWith('/\\')) {
    return '/'
  }
  return path
}
