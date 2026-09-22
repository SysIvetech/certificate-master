"""Certificate Master 서비스 모듈.

도메인별 서비스 구조:
- analytics/: 학습 분석 (진행도, 패턴, 속도)
- study/: 학습 계획 (생성, 추천)
- embedding/: 임베딩 및 벡터 스토어
- search/: 검색 (SearXNG, 크롤러)
- llm/: LLM 통합 (GPT, 정보 보강)

기존 import 경로 호환성 유지를 위해 re-export합니다.
"""

# ============================================================
# 기존 import 경로 호환성을 위한 re-export
# 예: from app.services.analytics_service import AnalyticsService
# ============================================================

# Analytics
from .analytics.analytics_service import AnalyticsService
from .analytics.learning_pattern_service import LearningPatternService
from .analytics.velocity_calculator import VelocityCalculator
from .embedding.factory import get_embedding_service

# Embedding
from .embedding.protocol import EmbeddingServiceProtocol
from .embedding.service import EmbeddingService
from .embedding.vector_store import VectorStoreService
from .llm.enrichment_service import CertificateEnrichmentService, get_enrichment_service

# LLM
from .llm.service import LLMService, get_llm_service
from .search.content_crawler import ContentCrawlerService
from .search.factory import get_search_service

# Search (SearXNG only)
from .search.protocol import SearchServiceProtocol
from .search.searxng_search import SearXNGSearchService
from .study.recommendation_service import RecommendationService

# Study
from .study.study_plan_service import StudyPlanService

# Aliases for backward compatibility
EnrichmentService = CertificateEnrichmentService
EmbeddingProtocol = EmbeddingServiceProtocol
SearchProtocol = SearchServiceProtocol
SearxngSearchService = SearXNGSearchService

__all__ = [
    # Analytics
    "AnalyticsService",
    "LearningPatternService",
    "VelocityCalculator",
    # Study
    "StudyPlanService",
    "RecommendationService",
    # Embedding
    "EmbeddingServiceProtocol",
    "EmbeddingProtocol",  # alias
    "EmbeddingService",
    "get_embedding_service",
    "VectorStoreService",
    # Search
    "SearchServiceProtocol",
    "SearchProtocol",  # alias
    "get_search_service",
    "SearXNGSearchService",
    "SearxngSearchService",  # alias
    "ContentCrawlerService",
    # LLM
    "LLMService",
    "get_llm_service",
    "CertificateEnrichmentService",
    "EnrichmentService",  # alias
    "get_enrichment_service",
]
