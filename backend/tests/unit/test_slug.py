"""Unit tests for slug functionality.

slug 필드 추가 및 slug 기반 조회 기능을 검증합니다.
"""

import uuid
from datetime import datetime, timezone

from app.models.certificate import Certificate as CertificateModel
from app.schemas.certificate import Certificate


class TestSlugInSchema:
    """Certificate 스키마에 slug 필드가 존재하는지 검증."""

    def test_certificate_schema_has_slug_field(self):
        """Certificate 응답 스키마에 slug 필드가 포함되어야 한다."""
        cert = Certificate(
            id="test-uuid",
            raw_id="S_테스트자격증",
            slug="테스트자격증",
            categories=[{"code": "S", "name": "국가전문자격"}],
            series="테스트",
            title="테스트자격증",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert cert.slug == "테스트자격증"

    def test_certificate_schema_slug_optional_with_default(self):
        """slug 필드는 Optional이며 기본값은 빈 문자열."""
        cert = Certificate(
            id="test-uuid",
            raw_id="S_테스트자격증",
            categories=[{"code": "S", "name": "국가전문자격"}],
            series="테스트",
            title="테스트자격증",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert cert.slug == ""


class TestSlugInModel:
    """Certificate 모델에 slug 컬럼이 존재하는지 검증."""

    def test_certificate_model_has_slug_column(self):
        """Certificate ORM 모델에 slug 컬럼이 있어야 한다."""
        assert hasattr(CertificateModel, "slug")

    def test_certificate_model_to_dict_includes_slug(self):
        """to_dict()에 slug 필드가 포함되어야 한다."""
        cert = CertificateModel()
        cert.id = str(uuid.uuid4())
        cert.title = "정보처리기사"
        cert.raw_id = "T_정보처리기사"
        cert.categories = [{"code": "T", "name": "국가기술자격"}]
        cert.slug = "정보처리기사"
        cert.created_at = datetime.now(timezone.utc)
        cert.updated_at = datetime.now(timezone.utc)

        d = cert.to_dict()
        assert "slug" in d
        assert d["slug"] == "정보처리기사"


class TestSlugGeneration:
    """Slug 생성 로직 테스트."""

    def test_simple_title(self):
        """단순 한글 제목은 그대로 slug가 된다."""
        from scripts.generate_slugs import generate_slug

        assert generate_slug("정보처리기사") == "정보처리기사"

    def test_title_with_parentheses(self):
        """괄호가 포함된 제목은 괄호를 제거하고 하이픈으로 연결."""
        from scripts.generate_slugs import generate_slug

        assert generate_slug("소방설비기사(전기분야)") == "소방설비기사-전기분야"

    def test_title_with_spaces(self):
        """공백은 하이픈으로 변환."""
        from scripts.generate_slugs import generate_slug

        assert generate_slug("사회 조사 분석사") == "사회-조사-분석사"

    def test_title_with_special_chars(self):
        """특수문자 제거."""
        from scripts.generate_slugs import generate_slug

        assert generate_slug("자격증/테스트!") == "자격증-테스트"

    def test_title_with_consecutive_hyphens(self):
        """연속 하이픈은 하나로 축소."""
        from scripts.generate_slugs import generate_slug

        assert generate_slug("자격증 (전기)") == "자격증-전기"


class TestSlugAPILookup:
    """API에서 UUID와 slug 모두로 조회 가능한지 검증하는 유틸리티 테스트."""

    def test_uuid_pattern_detection(self):
        """UUID 패턴 감지 함수가 올바르게 동작."""
        from app.api.v1.certificates import is_uuid

        assert is_uuid("ec9afe49-f699-4a69-a9a9-8d721361536e") is True
        assert is_uuid("정보처리기사") is False
        assert is_uuid("소방설비기사-전기분야") is False
        assert is_uuid("not-a-uuid") is False
        assert is_uuid("12345678-1234-1234-1234-123456789012") is True
