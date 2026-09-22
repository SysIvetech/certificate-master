"""SQLAlchemy 모델 테스트.

TDD Step 2: SQLAlchemy 모델 테스트
"""


class TestCertificateModel:
    """Certificate 모델 테스트."""

    def test_certificate_model_has_required_fields(self):
        """Certificate 모델이 필수 필드를 가지고 있는지 테스트."""
        from app.models.certificate import Certificate

        # 필수 컬럼 확인
        columns = Certificate.__table__.columns.keys()

        required_fields = [
            "id",
            "categories",  # code, category -> categories 배열로 변경
            "title",
            "raw_id",
            "overview",
            "difficulty",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert field in columns, f"'{field}' 필드가 Certificate 모델에 없습니다."

    def test_certificate_model_tablename(self):
        """Certificate 모델의 테이블 이름 확인."""
        from app.models.certificate import Certificate

        assert Certificate.__tablename__ == "certificates"

    def test_certificate_model_uuid_generation(self):
        """Certificate 모델 인스턴스 생성 시 UUID가 생성되는지 테스트."""
        from app.models.certificate import Certificate

        cert = Certificate(
            categories=[{"code": "T", "name": "국가기술자격"}],
            title="테스트자격증",
            raw_id="T_테스트자격증",
        )

        # id가 자동 생성되어야 함 (None이 아니거나, default가 설정되어 있어야 함)
        # 인스턴스 생성 시 default 함수가 호출됨
        assert (
            cert.id is not None
            or Certificate.__table__.columns["id"].default is not None
        )


class TestStudyPlanModel:
    """StudyPlan 모델 테스트."""

    def test_study_plan_model_has_required_fields(self):
        """StudyPlan 모델이 필수 필드를 가지고 있는지 테스트."""
        from app.models.study_plan import StudyPlan

        columns = StudyPlan.__table__.columns.keys()

        required_fields = [
            "id",
            "user_id",
            "certificate_id",
            "title",
            "target_date",
            "status",
            "created_at",
        ]

        for field in required_fields:
            assert field in columns, f"'{field}' 필드가 StudyPlan 모델에 없습니다."

    def test_study_plan_model_foreign_key(self):
        """StudyPlan 모델이 certificate_id FK를 가지고 있는지 테스트."""
        from app.models.study_plan import StudyPlan

        # Foreign key 확인
        fk_columns = [fk.column.name for fk in StudyPlan.__table__.foreign_keys]
        assert "id" in fk_columns  # certificates.id를 참조

    def test_study_plan_model_tablename(self):
        """StudyPlan 모델의 테이블 이름 확인."""
        from app.models.study_plan import StudyPlan

        assert StudyPlan.__tablename__ == "study_plans"


class TestCheckinModel:
    """Checkin 모델 테스트."""

    def test_checkin_model_has_required_fields(self):
        """Checkin 모델이 필수 필드를 가지고 있는지 테스트."""
        from app.models.checkin import Checkin

        columns = Checkin.__table__.columns.keys()

        required_fields = [
            "id",
            "user_id",
            "study_plan_id",
            "checkin_date",
            "hours_studied",
            "created_at",
        ]

        for field in required_fields:
            assert field in columns, f"'{field}' 필드가 Checkin 모델에 없습니다."

    def test_checkin_model_foreign_key(self):
        """Checkin 모델이 study_plan_id FK를 가지고 있는지 테스트."""
        from app.models.checkin import Checkin

        fk_columns = [fk.column.name for fk in Checkin.__table__.foreign_keys]
        assert "id" in fk_columns  # study_plans.id를 참조

    def test_checkin_model_tablename(self):
        """Checkin 모델의 테이블 이름 확인."""
        from app.models.checkin import Checkin

        assert Checkin.__tablename__ == "checkins"


class TestBaseModel:
    """Base 모델 테스트."""

    def test_declarative_base_exists(self):
        """SQLAlchemy DeclarativeBase가 존재하는지 테스트."""
        from app.models.base import Base

        assert Base is not None
        # DeclarativeBase의 metadata 확인
        assert hasattr(Base, "metadata")
