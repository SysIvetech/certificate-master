"""Certificate 모델의 domain 필드 테스트."""

from app.models.certificate import Certificate


def test_certificate_has_domain_field():
    """Certificate 모델에 domain 필드가 존재한다."""
    cert = Certificate(
        title="정보처리기사",
        raw_id="test_domain_cert",
        categories=[{"code": "T", "name": "국가기술자격"}],
        domain="IT/소프트웨어",
    )
    assert cert.domain == "IT/소프트웨어"


def test_certificate_domain_nullable():
    """domain 필드는 nullable이다."""
    cert = Certificate(
        title="테스트자격증",
        raw_id="test_domain_null",
        categories=[{"code": "T", "name": "국가기술자격"}],
    )
    assert cert.domain is None


def test_certificate_to_dict_includes_domain():
    """to_dict()에 domain 필드가 포함된다."""
    cert = Certificate(
        title="정보처리기사",
        raw_id="test_domain_dict",
        categories=[{"code": "T", "name": "국가기술자격"}],
        domain="IT/소프트웨어",
    )
    d = cert.to_dict()
    assert d["domain"] == "IT/소프트웨어"
