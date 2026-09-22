"""개선된 추천 시스템 테스트 스크립트.

쿼리 프롬프트와 도메인 필터링 개선 효과를 확인합니다.

사용법:
    uv run python -m scripts.test_improved_recommendation
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import sessionmaker

from app.core.database import get_engine
from app.schemas.recommendation import NaturalLanguageRequest
from app.services.study.natural_recommendation_service import (
    NaturalRecommendationService,
)


async def test_it_query():
    """IT 분야 추천 테스트."""
    print("=" * 80)
    print("개선된 추천 시스템 테스트: IT 분야")
    print("=" * 80)

    # 데이터베이스 세션
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # 테스트 쿼리
        user_input = "IT 분야 취업을 준비하고 있습니다. 비전공자인데 3개월 내에 딸 수 있는 자격증을 추천해주세요."

        print("\n[사용자 입력]")
        print(f"{user_input}")
        print()

        # 추천 서비스 생성
        service = NaturalRecommendationService(db=session)

        # 추천 생성
        request = NaturalLanguageRequest(user_input=user_input)
        response = await service.get_recommendations(request)

        # 결과 출력
        print("[1] 구조화된 컨텍스트")
        print("-" * 80)
        context = response.structured_context
        print(f"목표: {context.goal}")
        print(f"고용 상태: {context.employment_status}")
        print(f"전공 배경: {context.major_background}")
        print(f"주당 학습시간: {context.weekly_study_hours}시간")
        print(f"최대 준비기간: {context.max_study_period_days}일")
        print(f"난이도 선호: {context.difficulty_preference}")
        print(f"선호 산업: {', '.join(context.preferred_industries)}")

        print()
        print("[2] 생성된 검색 쿼리")
        print("-" * 80)
        print(response.query_used)

        print()
        print(f"[3] 추천 결과 ({response.total_matched}개 매칭)")
        print("-" * 80)

        if not response.recommendations:
            print("추천 결과 없음!")
        else:
            for idx, rec in enumerate(response.recommendations, 1):
                cert = rec.certificate
                print(f"\n#{idx} {cert.title} (점수: {rec.match_score}/100)")
                print(f"   계열: {cert.series}")
                print(f"   난이도: {cert.difficulty}/5")
                print(f"   준비기간: {cert.study_period_days}일")
                print(f"   추천이유: {rec.recommendation_reason}")

                # career_info 확인
                if cert.career_info:
                    industry = cert.career_info.get("industry", [])
                    related_jobs = cert.career_info.get("related_jobs", [])
                    print(
                        f"   산업분야: {', '.join(industry) if isinstance(industry, list) else industry}"
                    )
                    if related_jobs:
                        print(f"   관련직업: {', '.join(related_jobs[:3])}")

        print()
        print("=" * 80)
        print("테스트 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"[오류] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        session.close()


async def main():
    """메인 진입점."""
    await test_it_query()


if __name__ == "__main__":
    asyncio.run(main())
