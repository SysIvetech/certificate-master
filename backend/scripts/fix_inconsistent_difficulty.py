"""DB에 저장된 difficulty-study_period_days 비일관 데이터를 보정하는 스크립트.

동작 순서:
1. MariaDB에서 difficulty, study_period_days가 모두 NOT NULL인 자격증 조회
2. DIFFICULTY_PERIOD_RANGES 기준으로 비일관 레코드 탐지
3. study_period_days를 난이도 기준 허용 범위로 클램핑
4. --dry-run 모드에서는 변경 사항만 출력, --apply 모드에서 실제 DB 업데이트

사용법:
    cd backend && uv run python -m scripts.fix_inconsistent_difficulty          # dry-run
    cd backend && uv run python -m scripts.fix_inconsistent_difficulty --apply  # 실제 적용
"""

import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy.orm import sessionmaker

# backend 디렉토리를 path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

logger = logging.getLogger(__name__)

# 난이도별 허용 study_period_days 범위 (LLM 프롬프트 및 Pydantic 검증과 동기화)
DIFFICULTY_PERIOD_RANGES: dict[int, tuple[int, int]] = {
    1: (1, 21),  # 1~3주
    2: (14, 90),  # 2주~3개월
    3: (60, 210),  # 2~7개월
    4: (150, 540),  # 5개월~1.5년
    5: (300, 1095),  # 10개월~3년
}


def find_inconsistent_records(
    records: list[dict],
) -> list[dict]:
    """비일관 레코드를 탐지합니다.

    Args:
        records: id, title, difficulty, study_period_days를 포함하는 딕셔너리 리스트.

    Returns:
        비일관 레코드 리스트 (원본 딕셔너리 그대로).
    """
    inconsistent = []
    for rec in records:
        difficulty = rec.get("difficulty")
        study_days = rec.get("study_period_days")

        if difficulty is None or study_days is None:
            continue

        if difficulty not in DIFFICULTY_PERIOD_RANGES:
            inconsistent.append(rec)
            continue

        min_days, max_days = DIFFICULTY_PERIOD_RANGES[difficulty]
        if not (min_days <= study_days <= max_days):
            inconsistent.append(rec)

    return inconsistent


def compute_fix(difficulty: int, study_period_days: int) -> int:
    """difficulty 기준으로 보정된 study_period_days를 계산합니다.

    Args:
        difficulty: 난이도 (1-5).
        study_period_days: 현재 학습기간(일).

    Returns:
        보정된 study_period_days.
    """
    min_days, max_days = DIFFICULTY_PERIOD_RANGES.get(difficulty, (1, 1095))
    return max(min_days, min(study_period_days, max_days))


def main():
    """메인 실행 함수."""
    parser = argparse.ArgumentParser(
        description="difficulty-study_period_days 비일관 데이터 보정"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제 DB 업데이트 (기본값: dry-run)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    from app.core.database import get_engine
    from app.models.certificate import Certificate

    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        certs = (
            session.query(Certificate)
            .filter(
                Certificate.difficulty.isnot(None),
                Certificate.study_period_days.isnot(None),
            )
            .all()
        )

        records = [
            {
                "id": c.id,
                "title": c.title,
                "difficulty": c.difficulty,
                "study_period_days": c.study_period_days,
            }
            for c in certs
        ]

        logger.info(f"전체 레코드 수: {len(records)}")

        inconsistent = find_inconsistent_records(records)
        logger.info(f"비일관 레코드 수: {len(inconsistent)}")

        if not inconsistent:
            logger.info("보정할 레코드가 없습니다.")
            return

        for rec in inconsistent:
            old_days = rec["study_period_days"]
            new_days = compute_fix(rec["difficulty"], old_days)
            logger.info(
                f"  [{rec['id']}] {rec['title']}: "
                f"difficulty={rec['difficulty']}, "
                f"study_period_days {old_days} -> {new_days}"
            )

            if args.apply:
                session.query(Certificate).filter(Certificate.id == rec["id"]).update(
                    {"study_period_days": new_days}
                )

        if args.apply:
            session.commit()
            logger.info(f"{len(inconsistent)}건 업데이트 완료.")
        else:
            logger.info(
                f"[DRY-RUN] {len(inconsistent)}건 변경 예정. "
                f"실제 적용하려면 --apply 옵션을 사용하세요."
            )

    finally:
        session.close()


if __name__ == "__main__":
    main()
