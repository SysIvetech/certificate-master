"""기존 certificates 레코드에 slug 생성.

사용법:
    cd backend
    uv run python -m scripts.generate_slugs          # 전체 생성
    uv run python -m scripts.generate_slugs --dry-run # 미리보기

슬러그 규칙:
    - title에서 괄호 내용을 분리하여 하이픈으로 연결
    - 특수문자 제거, 공백→하이픈
    - 연속 하이픈 축소
    - 중복 시 첫 번째 카테고리 코드 접미사 (예: 정보처리기사-t)
"""

import re


def generate_slug(title: str) -> str:
    """title로부터 URL 슬러그를 생성.

    Args:
        title: 자격증명 (예: "정보처리기사", "소방설비기사(전기분야)")

    Returns:
        slug 문자열 (예: "정보처리기사", "소방설비기사-전기분야")
    """
    slug = title.strip()

    # 괄호를 하이픈으로 변환: "소방설비기사(전기분야)" → "소방설비기사-전기분야"
    slug = re.sub(r"\(", "-", slug)
    slug = re.sub(r"\)", "", slug)

    # 특수문자를 하이픈으로 변환 (한글, 영문, 숫자, 하이픈만 남김)
    slug = re.sub(r"[^\w가-힣a-zA-Z0-9\-]", "-", slug)

    # 언더스코어를 하이픈으로
    slug = slug.replace("_", "-")

    # 연속 하이픈 축소
    slug = re.sub(r"-+", "-", slug)

    # 앞뒤 하이픈 제거
    slug = slug.strip("-")

    return slug


def main():
    """기존 certificates에 slug를 생성하여 업데이트."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate slugs for certificates")
    parser.add_argument(
        "--dry-run", action="store_true", help="미리보기만 (DB 수정 안 함)"
    )
    args = parser.parse_args()

    # 환경 변수 로드
    from dotenv import load_dotenv

    load_dotenv()

    from sqlalchemy.orm import sessionmaker

    from app.core.database import get_engine
    from app.models.certificate import Certificate

    SessionLocal = sessionmaker(bind=get_engine())
    db = SessionLocal()
    try:
        certs = db.query(Certificate).all()
        print(f"총 {len(certs)}개 자격증 처리")

        # 1단계: 모든 slug 생성
        slug_map: dict[str, list] = {}  # slug → [cert1, cert2, ...]
        for cert in certs:
            slug = generate_slug(cert.title)
            if slug not in slug_map:
                slug_map[slug] = []
            slug_map[slug].append(cert)

        # 2단계: 중복 해결 및 할당
        updates = []
        for slug, cert_list in slug_map.items():
            if len(cert_list) == 1:
                updates.append((cert_list[0], slug))
            else:
                # 중복: 카테고리 코드 접미사 추가
                for cert in cert_list:
                    cat_code = ""
                    if cert.categories and len(cert.categories) > 0:
                        cat_code = cert.categories[0].get("code", "").lower()
                    if cat_code:
                        unique_slug = f"{slug}-{cat_code}"
                    else:
                        unique_slug = f"{slug}-{cert.id[:8]}"
                    updates.append((cert, unique_slug))

        # 3단계: 최종 중복 체크
        final_slugs: dict[str, str] = {}  # slug → cert.id
        for cert, slug in updates:
            if slug in final_slugs:
                # 극히 드문 경우: ID 접미사로 구분
                slug = f"{slug}-{cert.id[:8]}"
            final_slugs[slug] = cert.id

        # 4단계: 적용
        updated = 0
        for cert, slug in updates:
            # 최종 slug 확인
            actual_slug = slug
            if slug in final_slugs and final_slugs[slug] != cert.id:
                actual_slug = f"{slug}-{cert.id[:8]}"

            if args.dry_run:
                print(f"  {cert.title:30s} → {actual_slug}")
            else:
                cert.slug = actual_slug
                updated += 1

        if not args.dry_run:
            db.commit()
            print(f"{updated}개 slug 생성 완료")
        else:
            print(f"\n[DRY RUN] {len(updates)}개 slug 미리보기 완료 (DB 미변경)")

    finally:
        db.close()


if __name__ == "__main__":
    main()
