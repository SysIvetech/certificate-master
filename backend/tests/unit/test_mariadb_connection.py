"""MariaDB 연결 테스트.

TDD Step 1: 데이터베이스 연결 테스트
"""


class TestMariaDBConnection:
    """MariaDB 연결 관련 테스트."""

    def test_mariadb_engine_created(self):
        """SQLAlchemy 엔진이 생성되는지 테스트."""
        from app.core.database import get_engine

        engine = get_engine()

        assert engine is not None
        # MariaDB/MySQL은 'mysql' dialect 사용
        assert "mysql" in str(engine.url)

    def test_mariadb_url_correct_format(self):
        """MariaDB URL이 올바른 형식인지 테스트."""
        from app.core.database import get_mariadb_url

        # URL 형식 검증
        url = get_mariadb_url()
        assert "mysql+pymysql://" in url
        assert "certificate-master" in url

    def test_mariadb_session_created(self):
        """SQLAlchemy 세션이 생성되는지 테스트."""
        from app.core.database import get_db

        # get_db는 generator이므로 next()로 세션을 가져옴
        db_generator = get_db()
        db = next(db_generator)

        assert db is not None

        # 세션 닫기
        try:
            next(db_generator)
        except StopIteration:
            pass

    def test_mariadb_connection_works(self):
        """실제 MariaDB 연결이 동작하는지 테스트."""
        from sqlalchemy import text

        from app.core.database import get_engine

        engine = get_engine()

        # 간단한 쿼리로 연결 테스트
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS test"))
            row = result.fetchone()
            assert row[0] == 1

    def test_get_engine_is_singleton(self):
        """엔진이 싱글톤으로 생성되는지 테스트."""
        from app.core.database import get_engine

        engine1 = get_engine()
        engine2 = get_engine()

        # lru_cache로 인해 같은 객체여야 함
        assert engine1 is engine2
