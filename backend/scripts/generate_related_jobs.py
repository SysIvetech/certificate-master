"""related_jobs 필드 자동 생성 및 벡터 스토어 업데이트 스크립트.

LLM(GPT-5-nano)을 사용하여 자격증의 related_jobs 필드를 자동으로 생성하고
ChromaDB 벡터 스토어에도 업데이트합니다.

특징:
- related_jobs가 비어있는 자격증만 처리
- DB + 벡터 스토어 동시 업데이트
- 진행 상황 실시간 표시

사용법:
    # 샘플 50개 테스트
    uv run python -m scripts.generate_related_jobs --sample 50

    # 전체 실행
    uv run python -m scripts.generate_related_jobs --all
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from openai import AsyncOpenAI
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.core.database import get_engine
from app.models.certificate import Certificate
from app.services.embedding.vector_store import VectorStoreService

# LLM 프롬프트
RELATED_JOBS_PROMPT = """당신은 자격증 정보를 분석하여 관련 직업을 추출하는 전문가입니다.

다음 자격증 정보를 바탕으로 이 자격증과 관련된 직업(직무)을 3-5개 추출해주세요.

## 자격증 정보
- 제목: {title}
- 계열: {series}
- 산업분야: {industry}
- 개요: {overview}

## 출력 형식

반드시 JSON 형식으로만 출력하세요:
{{"related_jobs": ["직업1", "직업2", "직업3", ...]}}

## 규칙

1. 3-5개의 직업 추출
2. 구체적인 직업명 사용 (예: "개발자" X, "소프트웨어 개발자" O)
3. 자격증과 직접 관련 있는 직업만 포함
4. 한국어 직업명 사용
5. 중복 없이 명확하게

## 예시

입력: 정보처리기사, IT, 소프트웨어 개발 및 정보처리
출력: {{"related_jobs": ["소프트웨어 개발자", "시스템 엔지니어", "데이터베이스 관리자", "웹 개발자"]}}
"""


class RelatedJobsGenerator:
    """related_jobs 자동 생성기."""

    def __init__(self, db: Session):
        """초기화.

        Args:
            db: SQLAlchemy 세션
        """
        self.db = db
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
        self.model = self.settings.OPENAI_MODEL_NAME
        self.vector_store = VectorStoreService()

    def get_empty_related_jobs_certificates(
        self, limit: int = None
    ) -> list[Certificate]:
        """related_jobs가 비어있는 자격증 조회.

        Args:
            limit: 조회할 최대 개수 (None이면 전체)

        Returns:
            자격증 리스트
        """
        query = self.db.query(Certificate)

        # related_jobs가 없거나 비어있는 경우 필터링
        all_certs = query.all()
        empty_certs = []

        for cert in all_certs:
            career_info = cert.career_info or {}
            related_jobs = career_info.get("related_jobs", [])

            # None, 빈 리스트, 빈 문자열 모두 처리
            if not related_jobs or (
                isinstance(related_jobs, list) and len(related_jobs) == 0
            ):
                empty_certs.append(cert)

        if limit:
            return empty_certs[:limit]
        return empty_certs

    async def generate_related_jobs(self, certificate: Certificate) -> list[str]:
        """LLM으로 related_jobs 생성.

        Args:
            certificate: 자격증 객체

        Returns:
            관련 직업 리스트
        """
        print("  [LLM] 관련 직업 생성 시작...")

        career_info = certificate.career_info or {}
        industry = career_info.get("industry", [])
        if isinstance(industry, list):
            industry_str = ", ".join(industry)
        else:
            industry_str = str(industry)

        overview = certificate.overview or "정보 없음"

        print(
            f"  [LLM] 입력 - 제목: {certificate.title}, 계열: {certificate.series}, 산업: {industry_str}"
        )

        prompt = RELATED_JOBS_PROMPT.format(
            title=certificate.title,
            series=certificate.series,
            industry=industry_str,
            overview=overview[:200],  # 너무 길면 자름
        )

        try:
            print(f"  [LLM] API 호출 중... (model: {self.model})")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a career analyst expert."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                print("  [LLM] ❌ 응답 내용 없음")
                return []

            result = json.loads(content)
            related_jobs = result.get("related_jobs", [])

            print(f"  [LLM] ✅ 생성 완료: {related_jobs}")

            return related_jobs

        except Exception as e:
            print(f"  [LLM] ❌ 호출 실패: {e}")
            return []

    def update_certificate_related_jobs(
        self, certificate: Certificate, related_jobs: list[str]
    ) -> bool:
        """자격증의 related_jobs 업데이트 (DB).

        Args:
            certificate: 자격증 객체
            related_jobs: 관련 직업 리스트

        Returns:
            성공 여부
        """
        try:
            print(f"  [DB] 업데이트 시작 - ID: {certificate.id}")
            print(f"  [DB] 이전 career_info: {certificate.career_info}")

            career_info = certificate.career_info or {}
            career_info["related_jobs"] = related_jobs
            certificate.career_info = career_info

            # JSON 필드 변경을 SQLAlchemy에게 알림
            flag_modified(certificate, "career_info")

            print(f"  [DB] 변경 후 career_info: {certificate.career_info}")
            print("  [DB] 커밋 중...")

            self.db.commit()
            self.db.refresh(certificate)

            print(f"  [DB] ✅ 커밋 완료 - related_jobs: {career_info['related_jobs']}")
            return True

        except Exception as e:
            print(f"  [DB] ❌ 업데이트 실패: {e}")
            self.db.rollback()
            return False

    def update_vector_store_metadata(
        self, certificate: Certificate, related_jobs: list[str]
    ) -> bool:
        """벡터 스토어 메타데이터 업데이트.

        Args:
            certificate: 자격증 객체
            related_jobs: 관련 직업 리스트

        Returns:
            성공 여부
        """
        try:
            print(f"  [Vector] 업데이트 시작 - ID: {certificate.id}")

            # private 속성 _collection에 접근
            collection = self.vector_store._collection

            # 벡터 스토어에서 기존 메타데이터 가져오기
            print("  [Vector] 기존 메타데이터 조회 중...")
            records = collection.get(
                ids=[str(certificate.id)],
                include=["metadatas"],
            )

            if not records or not records["ids"]:
                print(f"  [Vector] ❌ 벡터 스토어에 ID {certificate.id} 없음")
                return False

            # 메타데이터 업데이트
            # 쉼표로 구분된 문자열로 저장 (예: "직업1, 직업2, 직업3")
            metadata = records["metadatas"][0]
            print(
                f"  [Vector] 이전 related_jobs: {metadata.get('related_jobs', 'N/A')}"
            )

            related_jobs_str = ", ".join(related_jobs)
            metadata["related_jobs"] = related_jobs_str

            print(f"  [Vector] 새 related_jobs: {related_jobs_str}")
            print("  [Vector] 업데이트 중...")

            # 업데이트
            collection.update(
                ids=[str(certificate.id)],
                metadatas=[metadata],
            )

            # 검증
            updated_records = collection.get(
                ids=[str(certificate.id)],
                include=["metadatas"],
            )
            final_related_jobs = updated_records["metadatas"][0].get("related_jobs")
            print(f"  [Vector] ✅ 업데이트 완료 - 최종값: {final_related_jobs}")

            return True

        except Exception as e:
            print(f"  [Vector] ❌ 업데이트 실패: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def process_certificate(
        self, certificate: Certificate, index: int, total: int
    ) -> dict:
        """자격증 하나 처리 (LLM 생성 + DB 업데이트 + 벡터 스토어 업데이트).

        Args:
            certificate: 자격증 객체
            index: 현재 인덱스
            total: 전체 개수

        Returns:
            처리 결과 딕셔너리
        """
        print(f"[{index}/{total}] {certificate.title}...", end=" ")

        # 1. LLM으로 related_jobs 생성
        related_jobs = await self.generate_related_jobs(certificate)

        if not related_jobs:
            print("FAIL (LLM)")
            return {
                "id": certificate.id,
                "title": certificate.title,
                "success": False,
                "error": "LLM generation failed",
            }

        # 2. DB 업데이트
        db_success = self.update_certificate_related_jobs(certificate, related_jobs)
        if not db_success:
            print("FAIL (DB)")
            return {
                "id": certificate.id,
                "title": certificate.title,
                "success": False,
                "error": "DB update failed",
            }

        # 3. 벡터 스토어 업데이트
        vector_success = self.update_vector_store_metadata(certificate, related_jobs)
        if not vector_success:
            print("FAIL (Vector)")
            return {
                "id": certificate.id,
                "title": certificate.title,
                "success": False,
                "error": "Vector store update failed",
            }

        print(f"OK ({len(related_jobs)})")
        return {
            "id": certificate.id,
            "title": certificate.title,
            "success": True,
            "related_jobs": related_jobs,
        }

    async def run(self, sample: int = None):
        """메인 실행 로직.

        Args:
            sample: 샘플 개수 (None이면 전체)
        """
        print("=" * 80)
        print("related_jobs 자동 생성 및 벡터 스토어 업데이트")
        print("=" * 80)

        # 1. related_jobs가 비어있는 자격증 조회
        print("\n[1] related_jobs가 비어있는 자격증 조회...")
        certificates = self.get_empty_related_jobs_certificates(limit=sample)

        print(f"총 {len(certificates)}개 발견")

        if not certificates:
            print("\n모든 자격증에 이미 related_jobs가 있습니다!")
            return

        if sample:
            print(f"샘플 모드: {sample}개만 처리")

        # 2. 처리
        print(f"\n[2] 처리 시작 ({len(certificates)}개)")
        print("-" * 80)

        results = []
        for idx, cert in enumerate(certificates, 1):
            result = await self.process_certificate(cert, idx, len(certificates))
            results.append(result)

            # 10개마다 진행 상황 출력
            if idx % 10 == 0:
                success_count = sum(1 for r in results if r["success"])
                print(f"  진행: {idx}/{len(certificates)} ({success_count} 성공)")

        # 3. 결과 요약
        print("\n" + "=" * 80)
        success_results = [r for r in results if r["success"]]
        fail_results = [r for r in results if not r["success"]]

        print(f"완료: 성공 {len(success_results)}개, 실패 {len(fail_results)}개")

        if fail_results:
            print("\n실패한 항목:")
            for fail in fail_results:
                print(f"  - {fail['title']}: {fail['error']}")

        print("\n" + "=" * 80)
        print("작업 완료!")
        print("=" * 80)


def main():
    """메인 함수."""
    parser = argparse.ArgumentParser(description="related_jobs 자동 생성")
    parser.add_argument(
        "--sample",
        type=int,
        help="샘플 개수 (예: --sample 50)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="전체 실행",
    )

    args = parser.parse_args()

    if args.all:
        sample = None
    elif args.sample:
        sample = args.sample
    else:
        print("사용법: --sample N 또는 --all")
        sys.exit(1)

    # DB 세션
    engine = get_engine()
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        generator = RelatedJobsGenerator(db)
        asyncio.run(generator.run(sample=sample))
    finally:
        db.close()


if __name__ == "__main__":
    main()
