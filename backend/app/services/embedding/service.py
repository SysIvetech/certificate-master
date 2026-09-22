"""자격증 텍스트 포맷팅 및 OpenAI 임베딩 생성 서비스.

이 서비스는:
1. 자격증 데이터를 임베딩용 텍스트로 포맷합니다.
2. OpenAI API를 사용하여 임베딩을 생성합니다.

OpenAI text-embedding-3-small: 1024차원, 빠르고 저렴

이 서비스는 EmbeddingServiceProtocol을 구현합니다.
"""

import logging
from typing import Optional

from openai import OpenAI

from app.core.config import get_settings
from app.utils.certificate_formatter import format_certificate_text

logger = logging.getLogger(__name__)


class EmbeddingService:
    """자격증 데이터 포맷팅 및 OpenAI 임베딩 생성 서비스.

    Attributes:
        _client: OpenAI 클라이언트 인스턴스 (싱글톤).
        model_name: 임베딩 모델 이름.
        dimensions: 임베딩 차원 (기본 1536).
    """

    _client: Optional[OpenAI] = None  # 클래스 레벨 싱글톤

    def __init__(self, api_key: Optional[str] = None):
        """서비스를 초기화합니다.

        Args:
            api_key: OpenAI API 키 (선택, 환경변수에서 자동 로드).
        """
        self.api_key = api_key
        settings = get_settings()
        self.model_name = settings.OPENAI_EMBEDDING_MODEL
        self.dimensions = settings.OPENAI_EMBEDDING_DIMENSIONS

    @classmethod
    def _get_client(cls) -> OpenAI:
        """OpenAI 클라이언트를 싱글톤으로 생성합니다.

        Returns:
            OpenAI 클라이언트 인스턴스.
        """
        if cls._client is None:
            settings = get_settings()
            cls._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return cls._client

    def create_embedding(self, text: str) -> list[float]:
        """단일 텍스트의 임베딩을 생성합니다.

        Args:
            text: 임베딩할 텍스트.

        Returns:
            임베딩 벡터 (dimensions 차원).
        """
        client = self._get_client()

        # 빈 텍스트 처리
        if not text or not text.strip():
            text = " "

        response = client.embeddings.create(
            model=self.model_name,
            input=text,
            dimensions=self.dimensions,
        )

        return response.data[0].embedding

    def create_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """여러 텍스트의 임베딩을 배치로 생성합니다.

        Args:
            texts: 임베딩할 텍스트 목록.

        Returns:
            각 텍스트에 대한 임베딩 벡터 목록.
        """
        if not texts:
            return []

        client = self._get_client()

        # 빈 텍스트 처리
        processed_texts = [t if t and t.strip() else " " for t in texts]

        # OpenAI API는 배치 처리 지원
        response = client.embeddings.create(
            model=self.model_name,
            input=processed_texts,
            dimensions=self.dimensions,
        )

        # 응답 순서 보장 (index로 정렬)
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    def format_certificate_for_embedding(self, cert: dict) -> str:
        """임베딩 생성을 위해 자격증 데이터를 포맷합니다.

        B4 수정: 공통 유틸리티 함수 사용으로 중복 제거.

        Args:
            cert: 자격증 데이터를 담은 딕셔너리.

        Returns:
            임베딩용으로 포맷된 텍스트 문자열.
        """
        return format_certificate_text(cert)
