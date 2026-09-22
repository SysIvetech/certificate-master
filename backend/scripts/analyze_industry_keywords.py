"""자격증 industry 키워드 분석 스크립트.

실제 자격증 데이터에서 industry 값을 수집하고 빈도를 분석합니다.
DOMAIN_INDUSTRY_MAPPING 업데이트에 활용합니다.

사용법:
    uv run python -m scripts.analyze_industry_keywords
"""

import sys
from collections import Counter
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import sessionmaker

from app.core.database import get_engine
from app.models.certificate import Certificate


def analyze_industries():
    """자격증의 industry 값을 분석합니다."""
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # 모든 자격증 조회
        certificates = session.query(Certificate).all()

        print("=" * 80)
        print(f"총 자격증 수: {len(certificates)}")
        print("=" * 80)

        # industry 값 수집
        industry_counter = Counter()
        industry_by_cert = {}

        for cert in certificates:
            career_info = cert.career_info or {}
            industry = career_info.get("industry", [])

            # 리스트 또는 문자열 처리
            if isinstance(industry, list):
                industry_list = industry
            elif industry:
                industry_list = [industry]
            else:
                industry_list = []

            # 빈도 집계
            for ind in industry_list:
                industry_counter[ind.strip()] += 1

            # 자격증별 저장
            if industry_list:
                industry_by_cert[cert.title] = industry_list

        # 빈도 높은 순으로 출력
        print("\n[1] Industry 키워드 빈도 (상위 50개)")
        print("-" * 80)

        for idx, (keyword, count) in enumerate(industry_counter.most_common(50), 1):
            percentage = (count / len(certificates)) * 100
            print(f"{idx:2d}. {keyword:30s}: {count:4d} ({percentage:5.1f}%)")

        # 도메인별 샘플 자격증
        print("\n[2] 도메인별 샘플 자격증 및 industry 값")
        print("-" * 80)

        # IT 관련 자격증 찾기
        print("\nIT 관련 자격증 샘플:")
        it_keywords = ["IT", "정보", "소프트웨어", "컴퓨터", "프로그래밍", "데이터"]
        it_certs = []

        for title, industries in industry_by_cert.items():
            industry_text = " ".join(industries).lower()
            if any(kw.lower() in industry_text for kw in it_keywords):
                it_certs.append((title, industries))

        for title, industries in it_certs[:10]:
            print(f"  - {title}")
            print(f"    Industry: {', '.join(industries)}")

        # 전자/제조 관련 자격증 찾기
        print("\n전자/제조 관련 자격증 샘플:")
        electronics_keywords = ["전자", "제조", "산업", "기계"]
        electronics_certs = []

        for title, industries in industry_by_cert.items():
            industry_text = " ".join(industries).lower()
            if any(kw in industry_text for kw in electronics_keywords):
                electronics_certs.append((title, industries))

        for title, industries in electronics_certs[:10]:
            print(f"  - {title}")
            print(f"    Industry: {', '.join(industries)}")

        print("\n" + "=" * 80)
        print("분석 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"[오류] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        session.close()


if __name__ == "__main__":
    analyze_industries()
