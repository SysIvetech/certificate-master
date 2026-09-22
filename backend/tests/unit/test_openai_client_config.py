"""OpenAI 클라이언트 타임아웃/재시도 설정 검증 테스트.

프록시 타임아웃(60s) 내에 fallback이 실행되도록
모든 LLM 서비스의 OpenAI 클라이언트가 올바른 설정을 갖는지 확인합니다.
"""

from unittest.mock import patch

from app.services.llm.context_extractor import (
    _LLM_MAX_RETRIES as EXTRACTOR_MAX_RETRIES,
)
from app.services.llm.context_extractor import (
    _LLM_TIMEOUT as EXTRACTOR_TIMEOUT,
)
from app.services.llm.context_extractor import (
    ContextExtractorService,
)
from app.services.study.reason_generator import (
    _LLM_MAX_RETRIES as REASON_MAX_RETRIES,
)
from app.services.study.reason_generator import (
    _LLM_TIMEOUT as REASON_TIMEOUT,
)
from app.services.study.reason_generator import (
    ReasonGeneratorService,
)

# ── 타임아웃 상수 검증 ──


def test_reason_generator_timeout_within_proxy_limit():
    """ReasonGenerator 타임아웃이 프록시 타임아웃(60s) 내에서 작동해야 한다.

    최악의 경우: timeout * (max_retries + 1) + backoff < 60s
    """
    worst_case = REASON_TIMEOUT * (REASON_MAX_RETRIES + 1)
    assert (
        worst_case < 60
    ), f"ReasonGenerator worst-case {worst_case}s exceeds 60s proxy timeout"


def test_context_extractor_timeout_within_proxy_limit():
    """ContextExtractor 타임아웃이 프록시 타임아웃(60s) 내에서 작동해야 한다."""
    worst_case = EXTRACTOR_TIMEOUT * (EXTRACTOR_MAX_RETRIES + 1)
    assert (
        worst_case < 60
    ), f"ContextExtractor worst-case {worst_case}s exceeds 60s proxy timeout"


# ── 클라이언트 인스턴스 설정 검증 ──


@patch("app.services.study.reason_generator.get_settings")
def test_reason_generator_client_has_timeout_and_retries(mock_settings):
    """ReasonGenerator의 AsyncOpenAI 클라이언트에 timeout과 max_retries가 설정되어야 한다."""
    mock_settings.return_value.OPENAI_API_KEY = "test-key"
    mock_settings.return_value.OPENAI_MODEL_NAME = "gpt-5-nano"

    service = ReasonGeneratorService(api_key="test-key")

    assert service.client is not None
    assert service.client.timeout == REASON_TIMEOUT
    assert service.client.max_retries == REASON_MAX_RETRIES


@patch("app.services.llm.context_extractor.get_settings")
def test_context_extractor_client_has_timeout_and_retries(mock_settings):
    """ContextExtractor의 AsyncOpenAI 클라이언트에 timeout과 max_retries가 설정되어야 한다."""
    mock_settings.return_value.OPENAI_API_KEY = "test-key"
    mock_settings.return_value.OPENAI_MODEL_NAME = "gpt-5-nano"

    service = ContextExtractorService(api_key="test-key")

    assert service.client is not None
    assert service.client.timeout == EXTRACTOR_TIMEOUT
    assert service.client.max_retries == EXTRACTOR_MAX_RETRIES


# ── max_retries 상한 검증 ──


def test_max_retries_is_reasonable():
    """max_retries는 2 이하여야 한다 (빠른 fallback 보장)."""
    assert REASON_MAX_RETRIES <= 2
    assert EXTRACTOR_MAX_RETRIES <= 2
