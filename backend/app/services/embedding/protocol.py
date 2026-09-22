"""임베딩 서비스 프로토콜 정의.

이 모듈은 임베딩 서비스의 공통 인터페이스를 정의합니다.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingServiceProtocol(Protocol):
    """임베딩 서비스 프로토콜.

    모든 임베딩 서비스 구현체가 따라야 하는 인터페이스입니다.

    Attributes:
        dimensions: 임베딩 벡터의 차원 수. ChromaDB 호환을 위해 1024 권장.
    """

    @property
    def dimensions(self) -> int:
        """임베딩 벡터의 차원 수를 반환합니다.

        Returns:
            임베딩 차원 수 (예: 1024).
        """
        ...

    def create_embedding(self, text: str) -> list[float]:
        """단일 텍스트의 임베딩을 생성합니다.

        Args:
            text: 임베딩할 텍스트.

        Returns:
            임베딩 벡터 (dimensions 차원).
        """
        ...

    def create_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """여러 텍스트의 임베딩을 배치로 생성합니다.

        Args:
            texts: 임베딩할 텍스트 목록.

        Returns:
            각 텍스트에 대한 임베딩 벡터 목록.
        """
        ...
