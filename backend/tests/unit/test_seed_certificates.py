"""seed_certificates.py 테스트.

TDD: Supabase → MariaDB 마이그레이션 테스트
"""

import json

import pytest

from scripts.seed_certificates import (
    CATEGORY_FILES,
    clear_certificates_mariadb,
    get_file_path_for_category,
    get_mariadb_session,
    load_certificates,
    seed_certificates_mariadb,
)


@pytest.fixture
def sample_certificates():
    """테스트용 샘플 자격증 데이터."""
    return [
        {
            "categories": [{"code": "S", "name": "국가전문자격"}],
            "series": "세무사",
            "title": "세무사",
            "raw_id": "S_세무사",
        },
        {
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "정보처리",
            "title": "정보처리기사",
            "raw_id": "T_정보처리기사",
        },
    ]


@pytest.fixture
def sample_json_file(sample_certificates, tmp_path):
    """테스트용 임시 JSON 파일 생성."""
    json_path = tmp_path / "test.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(sample_certificates, f, ensure_ascii=False)
    return json_path


class TestCategoryFiles:
    """카테고리 파일 매핑 테스트."""

    def test_category_files_has_all_categories(self):
        """모든 카테고리가 정의되어 있는지 확인."""
        expected = ["국가전문자격", "국가기술자격", "과정평가형자격", "일학습병행자격"]
        for cat in expected:
            assert cat in CATEGORY_FILES

    def test_category_files_has_correct_filenames(self):
        """카테고리별 파일명이 올바른지 확인."""
        assert CATEGORY_FILES["국가전문자격"] == "national_professional"
        assert CATEGORY_FILES["국가기술자격"] == "national_technical"
        assert CATEGORY_FILES["과정평가형자격"] == "course_evaluation"
        assert CATEGORY_FILES["일학습병행자격"] == "work_study"


class TestGetFilePathForCategory:
    """카테고리별 파일 경로 함수 테스트."""

    def test_returns_category_json_path(self, tmp_path):
        """카테고리 지정 시 해당 카테고리 JSON 경로 반환."""
        # by_category 디렉토리 생성
        by_cat_dir = tmp_path / "processed" / "by_category"
        by_cat_dir.mkdir(parents=True)

        # 테스트용 JSON 파일 생성
        test_file = by_cat_dir / "national_technical.json"
        test_file.write_text("[]", encoding="utf-8")

        result = get_file_path_for_category(tmp_path, "국가기술자격")

        assert result == test_file

    def test_returns_default_path_when_no_category(self, tmp_path):
        """카테고리 미지정 시 기본 경로 반환."""
        default_file = tmp_path / "processed" / "certificates_parsed.json"
        default_file.parent.mkdir(parents=True, exist_ok=True)
        default_file.write_text("[]", encoding="utf-8")

        result = get_file_path_for_category(tmp_path, None)

        assert result == default_file

    def test_raises_error_for_invalid_category(self, tmp_path):
        """잘못된 카테고리 시 에러 발생."""
        with pytest.raises(ValueError, match="Unknown category"):
            get_file_path_for_category(tmp_path, "잘못된카테고리")


class TestLoadCertificates:
    """자격증 로드 함수 테스트."""

    def test_load_returns_list(self, sample_json_file):
        """JSON 파일에서 리스트 반환."""
        result = load_certificates(sample_json_file)
        assert isinstance(result, list)

    def test_load_correct_count(self, sample_json_file):
        """올바른 개수 반환."""
        result = load_certificates(sample_json_file)
        assert len(result) == 2

    def test_load_preserves_data(self, sample_json_file):
        """데이터 구조 보존."""
        result = load_certificates(sample_json_file)
        assert result[0]["title"] == "세무사"
        assert result[1]["title"] == "정보처리기사"


class TestMariaDBIntegration:
    """MariaDB 통합 테스트 (Supabase 제거 후)."""

    def test_get_mariadb_session_returns_session(self):
        """MariaDB 세션이 반환되는지 테스트."""
        session = get_mariadb_session()
        assert session is not None
        session.close()

    def test_seed_certificates_inserts_data(self, sample_certificates):
        """자격증 데이터가 MariaDB에 삽입되는지 테스트."""
        # 테스트용 데이터에 TEST_ 접두어 추가 + 유니크한 제목
        test_certs = [
            {
                **cert,
                "raw_id": f"TEST_{cert['raw_id']}",
                "title": f"TEST_{cert['title']}",
            }
            for cert in sample_certificates
        ]

        session = get_mariadb_session()
        try:
            # 먼저 기존 테스트 데이터 정리
            clear_certificates_mariadb(session, raw_id_prefix="TEST_")

            # 삽입 테스트 (4개 반환: inserted, category_added, skipped, failed)
            inserted, category_added, skipped, failed = seed_certificates_mariadb(
                session, test_certs
            )

            assert inserted == 2
            assert failed == 0
        finally:
            # 테스트 데이터 정리
            clear_certificates_mariadb(session, raw_id_prefix="TEST_")
            session.close()

    def test_clear_certificates_removes_data(self, sample_certificates):
        """자격증 데이터가 삭제되는지 테스트."""
        # 테스트용 데이터에 TEST_ 접두어 추가 + 유니크한 제목
        test_certs = [
            {
                **cert,
                "raw_id": f"TEST_CLR_{cert['raw_id']}",
                "title": f"TEST_CLR_{cert['title']}",
            }
            for cert in sample_certificates
        ]

        session = get_mariadb_session()
        try:
            # 먼저 기존 테스트 데이터 정리
            clear_certificates_mariadb(session, raw_id_prefix="TEST_CLR_")

            # 먼저 데이터 삽입
            seed_certificates_mariadb(session, test_certs)

            # 삭제 테스트
            deleted = clear_certificates_mariadb(session, raw_id_prefix="TEST_CLR_")

            assert deleted >= 2
        finally:
            session.close()

    def test_seed_handles_duplicates(self, sample_certificates):
        """중복 데이터 처리 테스트 - 같은 title이면 카테고리만 추가."""
        test_certs = [
            {
                **cert,
                "raw_id": f"TEST_DUP_{cert['raw_id']}",
                "title": f"TEST_DUP_{cert['title']}",
            }
            for cert in sample_certificates
        ]

        session = get_mariadb_session()
        try:
            # 먼저 기존 테스트 데이터 정리
            clear_certificates_mariadb(session, raw_id_prefix="TEST_DUP_")

            # 첫 번째 삽입
            inserted, _, _, failed = seed_certificates_mariadb(session, test_certs)
            assert inserted == 2
            assert failed == 0

            # 동일 데이터 다시 삽입 (같은 title이면 건너뜀)
            inserted2, category_added, skipped, failed2 = seed_certificates_mariadb(
                session, test_certs
            )

            # 같은 카테고리이므로 건너뜀
            assert inserted2 == 0
            assert skipped == 2
            assert failed2 == 0
        finally:
            clear_certificates_mariadb(session, raw_id_prefix="TEST_DUP_")
            session.close()

    def test_seed_adds_category_to_existing(self, sample_certificates):
        """같은 title의 자격증에 다른 카테고리가 추가되는지 테스트."""
        test_certs = [
            {
                "categories": cert["categories"],
                "series": cert["series"],
                "title": f"TEST_CAT_{cert['title']}",
                "raw_id": f"TEST_CAT_{cert['raw_id']}",
            }
            for cert in sample_certificates
        ]

        session = get_mariadb_session()
        try:
            # 먼저 기존 테스트 데이터 정리
            clear_certificates_mariadb(session, raw_id_prefix="TEST_CAT_")

            # 첫 번째 삽입
            inserted, _, _, failed = seed_certificates_mariadb(session, test_certs)
            assert inserted == 2

            # 같은 title에 다른 카테고리로 삽입
            test_certs_new_category = [
                {
                    "categories": [{"code": "C", "name": "과정평가형자격"}],
                    "series": cert["series"],
                    "title": f"TEST_CAT_{cert['title']}",
                    "raw_id": f"TEST_CAT_C_{cert['raw_id']}",
                }
                for cert in sample_certificates
            ]
            inserted2, category_added, skipped, failed2 = seed_certificates_mariadb(
                session, test_certs_new_category
            )

            # 새 카테고리가 추가되어야 함
            assert inserted2 == 0
            assert category_added == 2
            assert failed2 == 0
        finally:
            clear_certificates_mariadb(session, raw_id_prefix="TEST_CAT_")
            session.close()
