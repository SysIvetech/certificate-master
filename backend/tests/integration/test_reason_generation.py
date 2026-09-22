"""추천 이유 생성 테스트.

개선된 프롬프트로 생성된 추천 이유의 품질을 확인합니다.
"""

import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.schemas.recommendation import StructuredUserContext
from app.services.study.reason_generator import ReasonGeneratorService


async def test_reason_generation():
    """추천 이유 생성 테스트."""
    print("=" * 80)
    print("Recommendation Reason Generation Test")
    print("=" * 80)

    service = ReasonGeneratorService()

    # 테스트 케이스 1: IT 취업 (비전공자)
    print("\n[Test 1] IT Software Developer (Non-major, 3 months)")
    print("-" * 80)

    context1 = StructuredUserContext(
        goal="취업",
        employment_status="학생",
        major_background="비전공자",
        weekly_study_hours=25,
        max_study_period_days=90,
        difficulty_preference="하",
        preferred_industries=["IT", "소프트웨어"],
    )

    cert1 = {
        "title": "정보처리기능사",
        "overview": "소프트웨어 개발 및 데이터베이스 기초",
        "career_info": {
            "industry": ["IT", "정보처리"],
            "related_jobs": ["프로그래머", "시스템 운영자", "웹 개발자"],
        },
        "feasibility_info": {"self_study_possible": True},
    }

    try:
        reason1 = await service.generate_reason(context1, cert1)
        print("User: 비전공자, IT 취업, 3개월")
        print("Cert: 정보처리기능사")
        print(f"\nReason ({len(reason1)} chars):")
        print(f'"{reason1}"')
        print()

        # 품질 검증
        checks = {
            "산업 분야 언급": any(
                kw in reason1 for kw in ["IT", "소프트웨어", "정보처리"]
            ),
            "목표 언급": any(kw in reason1 for kw in ["취업", "채용"]),
            "비전공자 언급": any(kw in reason1 for kw in ["비전공", "독학"]),
            "적절한 길이": 80 <= len(reason1) <= 200,
            "제외 키워드 없음": not any(
                kw in reason1 for kw in ["제조", "건설", "용접"]
            ),
        }

        print("Quality Checks:")
        for check, passed in checks.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {check}")

    except Exception as e:
        print(f"[ERROR] {e}")

    # 테스트 케이스 2: 금융 전문성 (재직자)
    print("\n" + "=" * 80)
    print("[Test 2] Finance Professional (Employed, 6 months)")
    print("-" * 80)

    context2 = StructuredUserContext(
        goal="전문성 강화",
        employment_status="재직 중",
        major_background="전공자",
        weekly_study_hours=10,
        max_study_period_days=180,
        difficulty_preference="중",
        preferred_industries=["금융", "회계"],
    )

    cert2 = {
        "title": "재무관리사",
        "overview": "기업 재무 관리 및 분석",
        "career_info": {
            "industry": ["금융", "재무"],
            "related_jobs": ["재무 담당자", "금융 분석가", "회계 담당자"],
        },
        "feasibility_info": {"self_study_possible": True},
    }

    try:
        reason2 = await service.generate_reason(context2, cert2)
        print("User: 재직자, 금융 전문성, 6개월")
        print("Cert: 재무관리사")
        print(f"\nReason ({len(reason2)} chars):")
        print(f'"{reason2}"')
        print()

        checks = {
            "산업 분야 언급": any(kw in reason2 for kw in ["금융", "재무", "회계"]),
            "목표 언급": any(kw in reason2 for kw in ["전문성", "승진", "경력"]),
            "재직자 언급": any(kw in reason2 for kw in ["재직", "실무", "현업"]),
            "적절한 길이": 80 <= len(reason2) <= 200,
        }

        print("Quality Checks:")
        for check, passed in checks.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {check}")

    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_reason_generation())
