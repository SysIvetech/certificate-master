"""ivetech auth-service JWT 검증 테스트 (app.core.security).

auth-service(jjwt)는 jwt.secret 을 Base64 디코딩한 키로 HMAC 서명하고,
키 길이에 따라 HS256/HS384/HS512 를 선택합니다. 여기서는 PyJWT 로 같은
형식의 토큰을 만들어 검증 로직을 확인합니다.
"""

import base64
import time
from types import SimpleNamespace

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core import security
from app.core.security import (
    AuthenticatedUser,
    MockUser,
    decode_access_token,
    get_current_user,
    get_current_user_optional,
)

pytestmark = pytest.mark.unit

KEY_64 = b"k" * 64  # jjwt 기준 HS512 가 선택되는 길이
SECRET_64 = base64.b64encode(KEY_64).decode()


def make_token(
    key: bytes = KEY_64,
    algorithm: str = "HS512",
    exp_offset: int = 600,
    **overrides,
) -> str:
    now = int(time.time())
    claims = {
        "sub": "42",
        "email": "user@example.com",
        "nickname": "tester",
        "roles": "USER,EXPERT",
        "iat": now,
        "exp": now + exp_offset,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm=algorithm)


@pytest.fixture
def auth_settings(monkeypatch):
    """security 모듈이 읽는 설정을 테스트용으로 교체."""

    def _apply(enabled: bool, secret: str | None = SECRET_64):
        monkeypatch.setattr(
            security,
            "get_settings",
            lambda: SimpleNamespace(AUTH_ENABLED=enabled, JWT_SECRET=secret),
        )

    return _apply


class TestDecodeAccessToken:
    def test_valid_token_returns_user(self):
        user = decode_access_token(make_token(), SECRET_64)

        assert isinstance(user, AuthenticatedUser)
        assert user.id == "42"
        assert user.email == "user@example.com"
        assert user.nickname == "tester"
        assert user.roles == ["USER", "EXPERT"]

    def test_hs256_with_short_key(self):
        key = b"s" * 32
        token = make_token(key=key, algorithm="HS256")

        user = decode_access_token(token, base64.b64encode(key).decode())

        assert user.id == "42"

    def test_secret_without_padding_is_accepted(self):
        key = b"x" * 33  # Base64 결과에 패딩이 붙는 길이
        secret = base64.b64encode(key).decode().rstrip("=")

        user = decode_access_token(make_token(key=key, algorithm="HS256"), secret)

        assert user.id == "42"

    def test_numeric_sub_is_converted_to_string(self):
        # jjwt 는 문자열 sub 를 쓰지만, 방어적으로 숫자도 문자열로 변환되는지 확인
        token = make_token(sub="7")
        assert decode_access_token(token, SECRET_64).id == "7"

    def test_missing_roles_gives_empty_list(self):
        token = make_token(roles=None)
        assert decode_access_token(token, SECRET_64).roles == []

    def test_expired_token_raises(self):
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(make_token(exp_offset=-10), SECRET_64)

    def test_wrong_secret_raises(self):
        other = base64.b64encode(b"z" * 64).decode()
        with pytest.raises(jwt.InvalidSignatureError):
            decode_access_token(make_token(), other)

    def test_refresh_token_without_sub_is_rejected(self):
        # auth-service refresh token 은 sub 없이 iat/exp 만 가짐
        refresh = make_token(sub=None, email=None, nickname=None, roles=None)
        with pytest.raises(jwt.MissingRequiredClaimError):
            decode_access_token(refresh, SECRET_64)

    def test_unsigned_token_is_rejected(self):
        unsigned = jwt.encode({"sub": "42", "exp": int(time.time()) + 60}, None, "none")
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(unsigned, SECRET_64)

    def test_invalid_base64_secret_raises_value_error(self):
        with pytest.raises(ValueError, match="Base64"):
            decode_access_token(make_token(), "not base64 !!")


class TestDependencies:
    """FastAPI 의존성 동작을 HTTP 요청으로 확인."""

    @pytest.fixture
    def client(self):
        app = FastAPI()

        @app.get("/required")
        async def required(user: AuthenticatedUser = Depends(get_current_user)):
            return {"id": user.id, "mock": isinstance(user, MockUser)}

        @app.get("/optional")
        async def optional(user=Depends(get_current_user_optional)):
            return {"id": user.id if user else None}

        return TestClient(app)

    def test_auth_disabled_returns_mock_user_without_token(self, client, auth_settings):
        auth_settings(enabled=False, secret=None)

        assert client.get("/required").json() == {
            "id": "mock-user-id-00000000",
            "mock": True,
        }
        assert client.get("/optional").json() == {"id": "mock-user-id-00000000"}

    def test_auth_enabled_requires_token(self, client, auth_settings):
        auth_settings(enabled=True)

        response = client.get("/required")

        assert response.status_code == 401
        assert response.json()["detail"] == "로그인이 필요합니다."
        assert response.headers["www-authenticate"] == "Bearer"

    def test_auth_enabled_accepts_valid_token(self, client, auth_settings):
        auth_settings(enabled=True)

        response = client.get(
            "/required", headers={"Authorization": f"Bearer {make_token()}"}
        )

        assert response.status_code == 200
        assert response.json() == {"id": "42", "mock": False}

    def test_auth_enabled_expired_token(self, client, auth_settings):
        auth_settings(enabled=True)

        response = client.get(
            "/required",
            headers={"Authorization": f"Bearer {make_token(exp_offset=-10)}"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "인증이 만료되었습니다."

    def test_auth_enabled_invalid_token(self, client, auth_settings):
        auth_settings(enabled=True)

        response = client.get("/required", headers={"Authorization": "Bearer garbage"})

        assert response.status_code == 401
        assert response.json()["detail"] == "인증 정보가 유효하지 않습니다."

    def test_optional_without_token_is_anonymous(self, client, auth_settings):
        auth_settings(enabled=True)

        assert client.get("/optional").json() == {"id": None}

    def test_optional_with_invalid_token_is_anonymous(self, client, auth_settings):
        auth_settings(enabled=True)

        response = client.get("/optional", headers={"Authorization": "Bearer garbage"})

        assert response.json() == {"id": None}

    def test_optional_with_valid_token(self, client, auth_settings):
        auth_settings(enabled=True)

        response = client.get(
            "/optional", headers={"Authorization": f"Bearer {make_token()}"}
        )

        assert response.json() == {"id": "42"}
