/**
 * ivetech 통합 인증 서비스(auth-service) 토큰 저장소
 *
 * rasang 프론트엔드와 동일한 방식:
 * - access token: 메모리에만 보관 (XSS로 localStorage에서 탈취되는 것 방지)
 * - refresh token: localStorage (새로고침 후 access token 재발급용)
 *
 * 주의: refresh token을 localStorage에 두는 방식은 XSS에 취약합니다.
 * auth-service가 httpOnly 쿠키를 지원하게 되면 이 모듈만 교체하면 됩니다.
 */

const REFRESH_TOKEN_KEY = 'cm_refresh_token'

let accessToken: string | null = null

export interface AccessTokenClaims {
  /** 사용자 ID (auth-service users.id) */
  sub: string
  email?: string
  nickname?: string
  /** 쉼표 구분 역할 (예: "USER") */
  roles?: string
  /** 만료 시각 (epoch seconds) */
  exp?: number
}

function base64UrlDecode(segment: string): string {
  const base64 = segment.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
  const binary = atob(padded)
  const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0))
  // 닉네임 등 한글 클레임을 위해 UTF-8로 디코딩
  return new TextDecoder().decode(bytes)
}

/**
 * JWT payload를 디코딩합니다. 서명 검증은 하지 않습니다(표시용).
 * 실제 검증은 certificate-master 백엔드가 JWT_SECRET으로 수행합니다.
 */
export function decodeAccessToken(token: string): AccessTokenClaims | null {
  try {
    const [, payload] = token.split('.')
    if (!payload) return null
    const claims = JSON.parse(base64UrlDecode(payload)) as AccessTokenClaims
    return claims?.sub ? claims : null
  } catch {
    return null
  }
}

/** 만료 30초 전부터는 만료된 것으로 간주 (시계 오차/요청 지연 대비) */
export function isAccessTokenExpired(token: string, skewSeconds = 30): boolean {
  const claims = decodeAccessToken(token)
  if (!claims?.exp) return true
  return claims.exp * 1000 <= Date.now() + skewSeconds * 1000
}

function safeLocalStorage(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage
  } catch {
    return null
  }
}

export const tokenManager = {
  getAccessToken: (): string | null => accessToken,

  /** 만료되지 않은 access token만 반환 */
  getValidAccessToken: (): string | null =>
    accessToken && !isAccessTokenExpired(accessToken) ? accessToken : null,

  getRefreshToken: (): string | null => safeLocalStorage()?.getItem(REFRESH_TOKEN_KEY) ?? null,

  setTokens: (access: string | null, refresh?: string | null) => {
    accessToken = access
    if (refresh !== undefined) {
      const storage = safeLocalStorage()
      if (refresh) storage?.setItem(REFRESH_TOKEN_KEY, refresh)
      else storage?.removeItem(REFRESH_TOKEN_KEY)
    }
  },

  clear: () => {
    accessToken = null
    safeLocalStorage()?.removeItem(REFRESH_TOKEN_KEY)
  },

  hasSession: (): boolean => !!accessToken || !!tokenManager.getRefreshToken(),
}
