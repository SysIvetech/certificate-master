/**
 * ivetech 통합 인증 서비스(auth-service) API 클라이언트
 *
 * 엔드포인트 (auth-service AuthController):
 * - POST /api/auth/signup   { email, password, nickname } → UserResponse
 * - POST /api/auth/login    { email, password }           → TokenResponse
 * - POST /api/auth/refresh  { refreshToken }              → TokenResponse (refresh token 교체)
 * - POST /api/auth/logout   (Authorization: Bearer)       → 204
 * - GET  /oauth2/authorization/google?redirect_uri=...    → Google 로그인 후 redirect_uri#access_token=..&refresh_token=..
 *
 * 오류 응답: { code, message, errors?: [{ field, value, reason }] }
 */

import type { AuthUser } from '@/types'
import { AUTH_API_URL, OAUTH_CALLBACK_PATH } from './config'
import { decodeAccessToken, tokenManager } from './token-manager'

interface TokenResponse {
  accessToken: string
  refreshToken: string
  tokenType: string
  expiresIn: number
}

interface AuthErrorBody {
  code?: string
  message?: string
  errors?: { field?: string; reason?: string }[]
}

export class AuthError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message)
    this.name = 'AuthError'
  }
}

// 사용자 존재 여부를 노출하지 않도록 로그인 실패는 같은 문구로 안내
const LOGIN_FAILURE_CODES = new Set(['U001', 'U003'])

async function toAuthError(response: Response): Promise<AuthError> {
  const body = (await response.json().catch(() => ({}))) as AuthErrorBody
  const reason = body.errors?.find((e) => e.reason)?.reason
  return new AuthError(
    reason || body.message || `요청에 실패했습니다. (HTTP ${response.status})`,
    response.status,
    body.code
  )
}

async function post<T>(path: string, body?: unknown, accessToken?: string): Promise<T> {
  if (!AUTH_API_URL) {
    throw new AuthError('인증 서버 주소(NEXT_PUBLIC_AUTH_API_URL)가 설정되지 않았습니다.', 0)
  }

  let response: Response
  try {
    response = await fetch(`${AUTH_API_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new AuthError('인증 서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.', 0)
  }

  if (!response.ok) {
    throw await toAuthError(response)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

/** access token 클레임을 화면용 사용자 정보로 변환 */
export function userFromAccessToken(token: string | null): AuthUser | null {
  if (!token) return null
  const claims = decodeAccessToken(token)
  if (!claims) return null
  return {
    id: claims.sub,
    email: claims.email ?? '',
    fullName: claims.nickname,
  }
}

function storeTokens(tokens: TokenResponse): AuthUser | null {
  tokenManager.setTokens(tokens.accessToken, tokens.refreshToken)
  return userFromAccessToken(tokens.accessToken)
}

export async function login(email: string, password: string): Promise<AuthUser | null> {
  try {
    const tokens = await post<TokenResponse>('/api/auth/login', { email, password })
    return storeTokens(tokens)
  } catch (error) {
    if (error instanceof AuthError && error.code && LOGIN_FAILURE_CODES.has(error.code)) {
      throw new AuthError('이메일 또는 비밀번호가 올바르지 않습니다.', error.status, error.code)
    }
    throw error
  }
}

export async function signup(email: string, password: string, nickname: string): Promise<void> {
  await post('/api/auth/signup', { email, password, nickname })
}

// 같은 탭에서 동시에 여러 요청이 401을 받아도 refresh는 한 번만 수행
let refreshInFlight: Promise<string | null> | null = null

/**
 * auth-service는 refresh 할 때마다 기존 refresh token을 폐기하고 새로 발급합니다(rotation).
 * 여러 탭이 같은 refresh token으로 동시에 갱신하면 한쪽이 실패하므로,
 * Web Locks로 탭 간에도 한 번에 하나만 갱신하고, 잠금을 얻은 뒤 최신 토큰을 다시 읽습니다.
 */
async function runRefresh(): Promise<string | null> {
  const refreshToken = tokenManager.getRefreshToken()
  if (!refreshToken) return null

  try {
    const tokens = await post<TokenResponse>('/api/auth/refresh', { refreshToken })
    tokenManager.setTokens(tokens.accessToken, tokens.refreshToken)
    return tokens.accessToken
  } catch (error) {
    // 인증 서버가 토큰을 거부한 경우에만 로그아웃 처리.
    // 네트워크 오류 등 일시적 실패로는 세션을 지우지 않습니다.
    const rejected = error instanceof AuthError && (error.status === 400 || error.status === 401)
    // 그 사이 다른 탭이 새 refresh token을 저장했다면 지우지 않음
    if (rejected && tokenManager.getRefreshToken() === refreshToken) {
      tokenManager.clear()
    }
    return null
  }
}

/**
 * refresh token으로 access token을 재발급합니다.
 * 실패하면 null을 반환합니다.
 */
export function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight

  const locks = typeof navigator !== 'undefined' ? navigator.locks : undefined
  const task: Promise<string | null> = locks?.request
    ? (async () => await locks.request('cm-auth-refresh', () => runRefresh()))()
    : runRefresh()

  refreshInFlight = task.finally(() => {
    refreshInFlight = null
  })
  return refreshInFlight
}

/** 유효한 access token을 반환 (만료됐으면 refresh 시도) */
export async function getAccessToken(): Promise<string | null> {
  return tokenManager.getValidAccessToken() ?? (await refreshAccessToken())
}

export async function logout(): Promise<void> {
  const accessToken = tokenManager.getValidAccessToken()
  try {
    // auth-service가 refresh token 삭제 + access token 블랙리스트 처리
    if (accessToken) {
      await post('/api/auth/logout', undefined, accessToken)
    }
  } catch {
    // 서버 로그아웃 실패와 무관하게 로컬 토큰은 제거
  } finally {
    tokenManager.clear()
  }
}

/** Google 로그인 시작 URL. 완료 후 이 사이트의 /oauth/callback 으로 돌아옵니다. */
export function getGoogleLoginUrl(): string {
  const redirectUri = `${window.location.origin}${OAUTH_CALLBACK_PATH}`
  return `${AUTH_API_URL}/oauth2/authorization/google?redirect_uri=${encodeURIComponent(redirectUri)}`
}
