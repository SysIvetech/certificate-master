"""리랭킹 시스템 테스트.

벡터 검색 결과를 도메인 매칭 점수로 재정렬하는 로직을 검증합니다.
"""

from app.services.study.reranker import DomainReranker

from app.models.certificate import Certificate


class TestDomainReranker:
    """도메인 기반 리랭커 테스트."""

    def test_boost_it_keywords_in_title(self):
        """IT 키워드가 제목에 있으면 점수를 부스팅해야 함."""
        reranker = DomainReranker()

        # IT 자격증 (제목에 "정보처리" 포함)
        it_cert = Certificate(
            id=1,
            title="정보처리기사",
            series="기사",
            difficulty=3,
            study_period_days=90,
            career_info={"industry": ["IT", "정보처리"]},
        )

        # 제조업 자격증
        manufacturing_cert = Certificate(
            id=2,
            title="제품응용모델링산업기사",
            series="산업기사",
            difficulty=3,
            study_period_days=90,
            career_info={"industry": ["제조", "기계"]},
        )

        # 동일한 벡터 유사도 점수 부여
        it_score = reranker.calculate_final_score(
            certificate=it_cert,
            vector_similarity=0.4,
            user_domains=["IT개발"],
        )

        manufacturing_score = reranker.calculate_final_score(
            certificate=manufacturing_cert,
            vector_similarity=0.4,
            user_domains=["IT개발"],
        )

        # IT 자격증 점수가 더 높아야 함
        assert it_score > manufacturing_score

    def test_penalize_excluded_keywords_in_title(self):
        """제외 키워드가 제목에 있으면 점수를 감점해야 함."""
        reranker = DomainReranker()

        # 건설 자격증 (제목에 "건축" 포함)
        construction_cert = Certificate(
            id=1,
            title="전산응용건축제도기능사",
            series="기능사",
            difficulty=2,
            study_period_days=60,
            career_info={"industry": ["건설", "건축"]},
        )

        # IT 자격증
        it_cert = Certificate(
            id=2,
            title="정보처리기능사",
            series="기능사",
            difficulty=2,
            study_period_days=60,
            career_info={"industry": ["IT"]},
        )

        construction_score = reranker.calculate_final_score(
            certificate=construction_cert,
            vector_similarity=0.45,
            user_domains=["IT개발"],
        )

        it_score = reranker.calculate_final_score(
            certificate=it_cert,
            vector_similarity=0.40,
            user_domains=["IT개발"],
        )

        # 벡터 유사도는 건설이 높지만, 제외 키워드 패널티로 IT가 더 높아야 함
        assert it_score > construction_score

    def test_industry_matching_boost(self):
        """산업 분야 매칭 시 점수 부스팅."""
        reranker = DomainReranker()

        # IT 산업 분야
        matching_cert = Certificate(
            id=1,
            title="정보처리산업기사",
            series="산업기사",
            difficulty=3,
            study_period_days=90,
            career_info={"industry": ["IT", "소프트웨어"]},
        )

        # 비매칭 산업 분야
        non_matching_cert = Certificate(
            id=2,
            title="기계설계산업기사",
            series="산업기사",
            difficulty=3,
            study_period_days=90,
            career_info={"industry": ["제조", "기계"]},
        )

        matching_score = reranker.calculate_final_score(
            certificate=matching_cert,
            vector_similarity=0.35,
            user_domains=["IT개발"],
        )

        non_matching_score = reranker.calculate_final_score(
            certificate=non_matching_cert,
            vector_similarity=0.35,
            user_domains=["IT개발"],
        )

        assert matching_score > non_matching_score

    def test_rerank_certificates(self):
        """전체 리랭킹 프로세스 테스트."""
        reranker = DomainReranker()

        certificates = [
            Certificate(
                id=1,
                title="제품응용모델링산업기사",
                series="산업기사",
                difficulty=3,
                study_period_days=90,
                career_info={"industry": ["제조", "CAD"]},
            ),
            Certificate(
                id=2,
                title="정보처리기사",
                series="기사",
                difficulty=3,
                study_period_days=90,
                career_info={"industry": ["IT", "정보처리"]},
            ),
            Certificate(
                id=3,
                title="정보처리기능사",
                series="기능사",
                difficulty=2,
                study_period_days=60,
                career_info={"industry": ["IT", "정보처리"]},
            ),
        ]

        # 벡터 유사도 점수 (제조업이 가장 높음)
        vector_scores = {1: 0.45, 2: 0.40, 3: 0.38}

        reranked = reranker.rerank(
            certificates=certificates,
            vector_scores=vector_scores,
            user_domains=["IT개발"],
        )

        # 리랭킹 후 IT 자격증이 상위권이어야 함
        assert reranked[0].id in [2, 3]
        assert reranked[1].id in [2, 3]
        assert reranked[2].id == 1  # 제조업은 하위권
