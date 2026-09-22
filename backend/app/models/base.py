"""SQLAlchemy Base 클래스.

모든 모델의 기반이 되는 DeclarativeBase 정의.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 모델의 기본 클래스.

    모든 ORM 모델은 이 클래스를 상속받아야 합니다.

    Example:
        ```python
        from app.models.base import Base
        from sqlalchemy import Column, String

        class User(Base):
            __tablename__ = "users"
            id = Column(String(36), primary_key=True)
            name = Column(String(100))
        ```
    """

    pass
