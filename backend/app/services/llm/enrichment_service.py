"""자격증 정보 보강을 수행하는 오케스트레이션 서비스.

Supabase에서 MariaDB로 마이그레이션됨 (2026-01-21).
검색 서비스: SearXNG 사용 (2026-01-28).
"""

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from app.services.llm.service import LLMService
from app.services.search.factory import get_search_service
from app.services.search.protocol import SearchServiceProtocol


class CertificateEnrichmentService:
    """자격증 정보를 검색·정제·저장하는 오케스트레이션 서비스."""

    def __init__(
        self,
        session: Session,
        search_service: Optional[SearchServiceProtocol] = None,
    ):
        """보강 서비스를 초기화합니다.

        Args:
            session: SQLAlchemy 세션 인스턴스.
            search_service: 검색 서비스 인스턴스. None이면 팩토리에서 생성.
        """
        self.session = session
        self.search = search_service or get_search_service()
        self.llm = LLMService()

    async def enrich_certificate(
        self, certificate_id: str, certificate_title: str
    ) -> Dict[str, Any]:
        """단일 자격증을 검색/정제해 MariaDB에 저장한다."""
        result = {
            "certificate_id": certificate_id,
            "certificate_title": certificate_title,
            "status": "in_progress",
        }

        try:
            # Step 1: 종합 검색 (7개 쿼리)
            print(
                f"\n[1/2] 종합 검색 시작: {certificate_title} (provider: {self.search.provider_name})"
            )
            search_results = await self.search.search_certificate_comprehensive(
                certificate_title
            )

            # Count total results
            total_results = sum(len(results) for results in search_results.values())
            print(f"  총 {total_results}개 검색 결과 수집 완료")

            # Format for LLM
            search_context = self.search.format_search_results_for_llm(search_results)

            # Step 2: Process with LLM (2-phase)
            print("[2/2] LLM 2단계 처리 중...")
            enrichment = await self.llm.enrich_certificate(
                certificate_title, search_context
            )

            # Post-process: Add newlines for readability
            enrichment = self._add_newlines(enrichment)

            # Log enrichment details
            print("  생성된 보강 데이터 요약:")
            print(f"    - 개요 글자수: {len(enrichment.overview)}")
            print(f"    - 난이도: {enrichment.difficulty}/5")
            print(f"    - 준비 기간: {enrichment.study_period_days}일")
            print(
                f"    - 시험 정보: {len(enrichment.exam_info.get('subjects', []))}개 과목"
            )
            print(
                f"    - 커리어 정보: {len(enrichment.career_info.get('use_cases', []))}개 활용 사례"
            )
            print(
                f"    - 후기 요약 여부: {bool(enrichment.user_reviews.get('summary'))}"
            )
            print(
                f"    - 학습 가이드: 방법 {len(enrichment.study_guide.get('study_methods', []))}개, 핵심 토픽 {len(enrichment.study_guide.get('key_exam_topics', []))}개"
            )
            print(
                f"    - 공식 출처 여부: {bool(enrichment.official_sources.get('official_site'))}"
            )
            print(f"    - 추천 강의: {len(enrichment.recommended_lectures)}개")
            # 취업준비생 관점 로깅 (NEW)
            print(
                f"    - 채용 시장 정보: 빈도={enrichment.job_market_info.get('job_posting_frequency', 'N/A')}"
            )
            print(
                f"    - 비용 정보: 총비용={enrichment.cost_breakdown.get('total_estimated_cost', 'N/A')}"
            )
            print(
                f"    - 합격 가능성: 독학={enrichment.feasibility_info.get('self_study_possible', 'N/A')}"
            )
            print(f"    - 유사 자격증: {len(enrichment.similar_certificates)}개")

            # Step 3: Update database (SQLAlchemy)
            print("[DB] 결과 저장 중...")

            # 자격증 조회
            cert = (
                self.session.query(Certificate)
                .filter(Certificate.id == certificate_id)
                .first()
            )

            if not cert:
                raise Exception(f"자격증을 찾을 수 없습니다: {certificate_id}")

            # 필드 업데이트
            cert.overview = enrichment.overview
            cert.difficulty = enrichment.difficulty
            cert.study_period_days = enrichment.study_period_days
            cert.exam_info = enrichment.exam_info
            cert.recommended_lectures = enrichment.recommended_lectures
            cert.career_info = enrichment.career_info
            cert.user_reviews = enrichment.user_reviews
            cert.study_guide = enrichment.study_guide
            cert.official_sources = enrichment.official_sources
            # 취업준비생 관점 필드 (NEW: 2026-01-28)
            cert.job_market_info = enrichment.job_market_info
            cert.cost_breakdown = enrichment.cost_breakdown
            cert.feasibility_info = enrichment.feasibility_info
            cert.exam_schedule_detail = enrichment.exam_schedule_detail
            cert.similar_certificates = enrichment.similar_certificates

            # 커밋
            self.session.commit()

            result["status"] = "success"
            result["enrichment"] = enrichment.model_dump()
            print("  [완료] 보강 데이터 저장 성공")

        except Exception as e:
            self.session.rollback()
            result["status"] = "error"
            result["error"] = str(e)
            print(f"  [ERROR] {str(e)}")

        return result

    def _add_newlines(self, enrichment):
        """긴 텍스트 필드에 줄바꿈을 추가해 가독성을 높입니다.

        Args:
            enrichment: CertificateEnrichment 객체

        Returns:
            줄바꿈이 반영된 enrichment 객체
        """
        # Add newlines to overview (after each sentence)
        if enrichment.overview:
            overview = enrichment.overview
            # Split by sentence endings and rejoin with newlines
            for char in [". ", "! ", "? "]:
                overview = overview.replace(char, char.strip() + ".\n")
            enrichment.overview = overview.replace(".\n", ".\n").rstrip("\n")

        # Add newlines to job_prospects
        if enrichment.career_info.get("job_prospects"):
            prospects = enrichment.career_info["job_prospects"]
            for char in [". ", "! ", "? "]:
                prospects = prospects.replace(char, char.strip() + ".\n")
            enrichment.career_info["job_prospects"] = prospects.rstrip("\n")

        # Add newlines to user_reviews.summary (paragraph breaks)
        if enrichment.user_reviews.get("summary"):
            summary = enrichment.user_reviews["summary"]
            sentences = []
            temp = ""
            for char in summary:
                temp += char
                if char in ".!?" and len(temp) > 50:
                    sentences.append(temp.strip())
                    temp = ""
            if temp:
                sentences.append(temp.strip())

            # Join with newlines (2 sentences per paragraph)
            paragraphs = []
            for i in range(0, len(sentences), 2):
                para = " ".join(sentences[i : i + 2])
                paragraphs.append(para)
            enrichment.user_reviews["summary"] = "\n\n".join(paragraphs)

        # Add newlines to difficulty_feedback
        if enrichment.user_reviews.get("difficulty_feedback"):
            feedback = enrichment.user_reviews["difficulty_feedback"]
            for char in [". ", "! ", "? "]:
                feedback = feedback.replace(char, char.strip() + ".\n")
            enrichment.user_reviews["difficulty_feedback"] = feedback.rstrip("\n")

        return enrichment


# Singleton instance
_enrichment_service: Optional[CertificateEnrichmentService] = None


def get_enrichment_service(
    session: Session,
    search_service: Optional[SearchServiceProtocol] = None,
) -> CertificateEnrichmentService:
    """Certificate Enrichment Service 인스턴스를 반환합니다.

    Args:
        session: SQLAlchemy 세션 인스턴스.
        search_service: 검색 서비스 인스턴스. None이면 기본 서비스 사용.

    Returns:
        CertificateEnrichmentService 인스턴스.
    """
    # Note: Not using singleton pattern since service needs session
    return CertificateEnrichmentService(session, search_service=search_service)
