"""로깅 설정 테스트.

라이브러리 로그 억제 및 에러 메시지 명확화를 테스트합니다.
"""

import logging


class TestLoggingConfig:
    """로깅 설정 테스트."""

    def test_suppress_library_logs(self):
        """라이브러리 로그가 억제되는지 확인."""
        from scripts.data_pipeline import setup_logging

        # 로깅 설정 적용
        setup_logging(verbose=False)

        # 라이브러리 로거 레벨 확인 (CRITICAL = 50)
        assert logging.getLogger("trafilatura").level >= logging.CRITICAL
        assert logging.getLogger("httpx").level >= logging.WARNING
        assert logging.getLogger("urllib3").level >= logging.CRITICAL
        assert logging.getLogger("httpcore").level >= logging.WARNING

    def test_verbose_mode_still_suppresses_library_logs(self):
        """verbose 모드에서도 라이브러리 로그는 억제."""
        from scripts.data_pipeline import setup_logging

        setup_logging(verbose=True)

        # verbose 모드에서도 라이브러리 로그는 억제
        assert logging.getLogger("trafilatura").level >= logging.CRITICAL
        assert logging.getLogger("urllib3").level >= logging.CRITICAL
