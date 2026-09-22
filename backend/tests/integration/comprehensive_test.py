"""종합 추천 시스템 E2E 테스트.

모든 개선 사항의 효과를 확인합니다:
1. 쿼리 생성 프롬프트 개선
2. 리랭킹 시스템
3. 추천 이유 생성 개선
"""

import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import sessionmaker

from app.core.database import get_engine
from app.schemas.recommendation import NaturalLanguageRequest
from app.services.study.natural_recommendation_service import (
    NaturalRecommendationService,
)


async def comprehensive_test():
    """종합 E2E 테스트."""
    print("=" * 80)
    print("COMPREHENSIVE RECOMMENDATION SYSTEM TEST")
    print("=" * 80)
    print("\nTesting all improvements:")
    print("1. Query generation prompt (enhanced)")
    print("2. Reranking system (domain matching)")
    print("3. Recommendation reason generation (improved)")
    print()

    # 데이터베이스 세션
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # 테스트 1: IT 취업 (비전공자, 3개월)
        await test_it_job_search(session)

        # 테스트 2: 금융 전문성 (재직자, 6개월)
        await test_finance_expertise(session)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()
    finally:
        session.close()


async def test_it_job_search(session):
    """IT 취업 테스트."""
    print("\n" + "=" * 80)
    print("[TEST 1] IT Job Search - Non-major, 3 months")
    print("=" * 80)

    user_input = (
        "IT 분야 취업을 준비하고 있습니다. "
        "비전공자인데 3개월 내에 딸 수 있는 자격증을 추천해주세요."
    )

    print("\n[User Input]")
    print(f'"{user_input}"')

    service = NaturalRecommendationService(db=session)
    request = NaturalLanguageRequest(user_input=user_input)

    response = await service.get_recommendations(request)

    # 1. 구조화된 컨텍스트
    print("\n[1] Structured Context")
    print("-" * 80)
    ctx = response.structured_context
    print(f"Goal: {ctx.goal}")
    print(f"Background: {ctx.major_background}")
    print(f"Employment: {ctx.employment_status}")
    print(f"Study Hours: {ctx.weekly_study_hours}h/week")
    print(f"Max Period: {ctx.max_study_period_days} days")
    print(f"Industries: {', '.join(ctx.preferred_industries)}")

    # 2. 생성된 쿼리
    print("\n[2] Generated Query (Enhanced)")
    print("-" * 80)
    print(f"{response.query_used[:150]}...")

    # 3. 추천 결과
    print(f"\n[3] Top 5 Recommendations (Total: {response.total_matched})")
    print("-" * 80)

    if not response.recommendations:
        print("No recommendations!")
        return

    it_keywords = ["정보처리", "소프트웨어", "컴퓨터", "프로그래밍", "IT"]
    it_count = 0

    for idx, rec in enumerate(response.recommendations[:5], 1):
        cert = rec.certificate
        is_it = any(kw in cert.title for kw in it_keywords)
        if is_it:
            it_count += 1

        marker = "[IT]" if is_it else "    "
        print(f"\n{marker} #{idx} {cert.title} (Score: {rec.match_score}/100)")
        print(f"      Series: {cert.series}, Difficulty: {cert.difficulty}/5")
        print(f"      Period: {cert.study_period_days} days")

        # 산업 분야
        if cert.career_info:
            industry = cert.career_info.get("industry", [])
            if industry:
                print(f"      Industry: {', '.join(industry[:3])}")

        # 추천 이유 (개선된 프롬프트 적용)
        print(f'      Reason: "{rec.recommendation_reason}"')

    # 4. 품질 평가
    print("\n[4] Quality Assessment")
    print("-" * 80)
    print(f"IT certificates in top 5: {it_count}/5")

    if it_count >= 3:
        print("[SUCCESS] Good IT certificate ranking!")
    else:
        print("[WARNING] Few IT certificates in top 5")

    # 추천 이유 품질 체크
    if response.recommendations:
        first_reason = response.recommendations[0].recommendation_reason
        reason_checks = {
            "Mentions IT/Software": any(
                kw in first_reason for kw in ["IT", "소프트웨어", "정보"]
            ),
            "Mentions goal (취업)": any(kw in first_reason for kw in ["취업", "채용"]),
            "Mentions non-major": any(kw in first_reason for kw in ["비전공", "독학"]),
            "Appropriate length": 80 <= len(first_reason) <= 200,
        }

        print("\nReason Quality (1st recommendation):")
        for check, passed in reason_checks.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {check}")


async def test_finance_expertise(session):
    """금융 전문성 테스트."""
    print("\n" + "=" * 80)
    print("[TEST 2] Finance Expertise - Employed, 6 months")
    print("=" * 80)

    user_input = (
        "금융권에서 일하고 있습니다. "
        "전문성을 키우고 싶은데 6개월 정도 준비할 수 있는 자격증 추천해주세요."
    )

    print("\n[User Input]")
    print(f'"{user_input}"')

    service = NaturalRecommendationService(db=session)
    request = NaturalLanguageRequest(user_input=user_input)

    response = await service.get_recommendations(request)

    # 구조화된 컨텍스트
    print("\n[1] Structured Context")
    print("-" * 80)
    ctx = response.structured_context
    print(f"Goal: {ctx.goal}")
    print(f"Employment: {ctx.employment_status}")
    print(f"Industries: {', '.join(ctx.preferred_industries)}")

    # 추천 결과
    print(f"\n[2] Top 3 Recommendations (Total: {response.total_matched})")
    print("-" * 80)

    if not response.recommendations:
        print("No recommendations!")
        return

    finance_keywords = ["금융", "회계", "세무", "재무", "보험"]
    finance_count = 0

    for idx, rec in enumerate(response.recommendations[:3], 1):
        cert = rec.certificate
        is_finance = any(kw in cert.title for kw in finance_keywords)
        if is_finance:
            finance_count += 1

        marker = "[FIN]" if is_finance else "     "
        print(f"\n{marker} #{idx} {cert.title} (Score: {rec.match_score}/100)")

        if cert.career_info:
            industry = cert.career_info.get("industry", [])
            if industry:
                print(f"       Industry: {', '.join(industry[:2])}")

        print(f'       Reason: "{rec.recommendation_reason}"')

    # 품질 평가
    print("\n[3] Quality Assessment")
    print("-" * 80)
    print(f"Finance certificates in top 3: {finance_count}/3")

    if finance_count >= 2:
        print("[SUCCESS] Good finance certificate ranking!")
    else:
        print("[WARNING] Few finance certificates in top 3")


if __name__ == "__main__":
    print("\n[NOTE] This test involves LLM calls and may take 1-2 minutes.\n")
    asyncio.run(comprehensive_test())
    print("\n" + "=" * 80)
    print("COMPREHENSIVE TEST COMPLETE")
    print("=" * 80)
