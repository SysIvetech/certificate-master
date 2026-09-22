"""기존 자격증에 도메인을 자동 분류하는 스크립트.

1차: 제목 키워드 기반 규칙 분류
2차: job_market_info.preferred_industries 기반 보조 분류
3차: 분류 불가 → "기타"

사용법:
    uv run python -m scripts.classify_domains --dry-run  # 미리보기
    uv run python -m scripts.classify_domains             # 실행
"""

import argparse
import sys

from sqlalchemy.orm import Session

from app.core.database import get_engine
from app.core.domains import (
    INDUSTRY_KEYWORD_TO_DOMAIN,
    TITLE_KEYWORD_TO_DOMAIN,
)
from app.models.certificate import Certificate


def classify_certificate(cert: Certificate) -> str:
    """자격증의 도메인을 분류한다."""
    title = cert.title or ""

    # 1차: 제목 키워드 매칭
    for keyword, domain in TITLE_KEYWORD_TO_DOMAIN.items():
        if keyword in title:
            return domain

    # 2차: preferred_industries 매칭
    job_market = cert.job_market_info or {}
    industries = job_market.get("preferred_industries", [])
    if isinstance(industries, list):
        for industry in industries:
            for keyword, domain in INDUSTRY_KEYWORD_TO_DOMAIN.items():
                if keyword in str(industry):
                    return domain

    # 3차: 분류 불가
    return "기타"


def main():
    parser = argparse.ArgumentParser(description="자격증 도메인 분류")
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 미리보기만")
    args = parser.parse_args()

    from sqlalchemy.orm import sessionmaker

    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    session: Session = SessionLocal()

    try:
        certs = session.query(Certificate).all()
        print(f"총 {len(certs)}개 자격증 분류 시작...")

        domain_counts: dict[str, int] = {}
        classified = 0

        for cert in certs:
            domain = classify_certificate(cert)
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

            if not args.dry_run:
                cert.domain = domain
                classified += 1

        # 결과 출력
        print("\n--- 분류 결과 ---")
        for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
            print(f"  {domain}: {count}개")
        print(f"  합계: {sum(domain_counts.values())}개")

        if args.dry_run:
            print("\n[DRY RUN] 실제 변경 없음")
        else:
            session.commit()
            print(f"\n{classified}개 자격증 도메인 분류 완료")

    except Exception as e:
        session.rollback()
        print(f"오류: {e}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
