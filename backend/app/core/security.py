"""Authentication utilities.

ivetech 통합 인증 서비스(auth-service)가 발급한 access token(JWT)을 검증합니다.

auth-service(common-security JwtTokenProvider) 토큰 형식:
- 서명: HMAC-SHA (jwt.secret 을 Base64 디코딩한 키, 키 길이에 따라 HS256/384/512)
- sub: 사용자 ID (숫자 문자열)
- email, nickname, roles(쉼표 구분) 클레임
- refresh token 에는 sub 가 없으므로 access token 자리에 쓰면 거부됩니다.

AUTH_ENABLED=False(기본값)면 토큰을 검증하지 않고 모든 요청을 MockUser로 처리합니다.
(제한 공개 기간 동안의 기존 동작 유지)

참고: 로그아웃 시 auth-service는 access token을 Redis 블랙리스트에 올리지만,
이 서비스는 서명과 만료만 검증합니다. 로그아웃한 토큰은 만료(기본 30분)까지 유효합니다.
"""

import base64
import binascii
import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

logger = logging.getLogger(__name__)

# auth-service 키 길이에 따라 HS256/384/512 중 하나로 서명됨
_ALLOWED_ALGORITHMS = ["HS256", "HS384", "HS512"]

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    """auth-service JWT 로 인증된 사용자.

    Attributes:
        id: 사용자 ID (auth-service users.id, 문자열).
        email: 이메일.
        nickname: 닉네임.
        roles: 역할 목록 (예: ["USER"]).
    """

    def __init__(
        self,
        id: str,
        email: Optional[str] = None,
        nickname: Optional[str] = None,
        roles: Optional[list[str]] = None,
    ):
        self.id = id
        self.email = email
        self.nickname = nickname
        self.roles = roles or []

    def __repr__(self) -> str:
        return f"AuthenticatedUser(id={self.id}, email={self.email})"


class MockUser(AuthenticatedUser):
    """AUTH_ENABLED=False 일 때 사용하는 고정 사용자."""

    def __init__(self):
        super().__init__(id="mock-user-id-00000000", email="mock@example.com")


def _decode_secret(secret: str) -> bytes:
    """jjwt Decoders.BASE64 와 동일하게 Base64 시크릿을 키 바이트로 변환."""
    padded = secret.strip() + "=" * (-len(secret.strip()) % 4)
    try:
        return base64.b64decode(padded, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError("JWT_SECRET 은 Base64 인코딩 문자열이어야 합니다.") from e


def decode_access_token(token: str, secret: str) -> AuthenticatedUser:
    """access token 을 검증하고 사용자 정보를 반환합니다.

    Raises:
        jwt.ExpiredSignatureError: 토큰 만료.
        jwt.InvalidTokenError: 서명 불일치, 형식 오류, sub 누락 등.
    """
    claims = jwt.decode(
        token,
        _decode_secret(secret),
        algorithms=_ALLOWED_ALGORITHMS,
        options={"require": ["sub", "exp"]},
    )
    roles_claim = claims.get("roles") or ""
    roles = [r.strip() for r in str(roles_claim).split(",") if r.strip()]
    return AuthenticatedUser(
        id=str(claims["sub"]),
        email=claims.get("email"),
        nickname=claims.get("nickname"),
        roles=roles,
    )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """인증 필수 엔드포인트용 의존성. 인증 비활성화 시 MockUser 반환."""
    settings = get_settings()
    if not settings.AUTH_ENABLED:
        return MockUser()

    if credentials is None or not credentials.credentials:
        raise _unauthorized("로그인이 필요합니다.")

    try:
        return decode_access_token(credentials.credentials, settings.JWT_SECRET or "")
    except jwt.ExpiredSignatureError:
        raise _unauthorized("인증이 만료되었습니다.")
    except (jwt.InvalidTokenError, ValueError) as e:
        logger.info("Invalid access token: %s", type(e).__name__)
        raise _unauthorized("인증 정보가 유효하지 않습니다.")


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[AuthenticatedUser]:
    """인증 선택 엔드포인트용 의존성. 토큰이 없거나 유효하지 않으면 None."""
    settings = get_settings()
    if not settings.AUTH_ENABLED:
        return MockUser()

    if credentials is None or not credentials.credentials:
        return None

    try:
        return decode_access_token(credentials.credentials, settings.JWT_SECRET or "")
    except (jwt.InvalidTokenError, ValueError):
        return None
