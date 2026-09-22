"""Unit tests for Checkin schema validation.

This module tests the consistency between database schema and Pydantic models.
"""

import pytest

from app.schemas.checkin import Checkin, CheckinCreate, CheckinUpdate


def test_checkin_create_has_hours_studied_field():
    """테스트: CheckinCreate 스키마에 hours_studied 필드가 있는지 확인.

    DB 컬럼명과 API 스키마가 일치해야 합니다.
    DB: hours_studied (수정 후)
    API: hours_studied
    """
    # Given: 체크인 생성 데이터
    data = {
        "study_plan_id": "123e4567-e89b-12d3-a456-426614174000",
        "hours_studied": 2.5,
        "notes": "테스트 학습",
        "mood": "good",
    }

    # When: CheckinCreate 객체 생성
    checkin_create = CheckinCreate(**data)

    # Then: hours_studied 필드가 존재하고 값이 올바름
    assert hasattr(checkin_create, "hours_studied")
    assert checkin_create.hours_studied == 2.5


def test_checkin_update_has_hours_studied_field():
    """테스트: CheckinUpdate 스키마에 hours_studied 필드가 있는지 확인."""
    # Given: 체크인 업데이트 데이터
    data = {
        "hours_studied": 3.0,
    }

    # When: CheckinUpdate 객체 생성
    checkin_update = CheckinUpdate(**data)

    # Then: hours_studied 필드가 존재
    assert hasattr(checkin_update, "hours_studied")
    assert checkin_update.hours_studied == 3.0


def test_checkin_response_has_hours_studied_field():
    """테스트: Checkin 응답 스키마에 hours_studied 필드가 있는지 확인."""
    # Given: 체크인 응답 데이터
    from datetime import date, datetime

    data = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "study_plan_id": "123e4567-e89b-12d3-a456-426614174001",
        "user_id": "123e4567-e89b-12d3-a456-426614174002",
        "checkin_date": date(2026, 1, 8),
        "hours_studied": 2.5,
        "notes": "테스트",
        "mood": "good",
        "created_at": datetime(2026, 1, 8, 10, 0, 0),
    }

    # When: Checkin 객체 생성
    checkin = Checkin(**data)

    # Then: hours_studied 필드가 존재
    assert hasattr(checkin, "hours_studied")
    assert checkin.hours_studied == 2.5


def test_hours_studied_validation():
    """테스트: hours_studied 필드의 유효성 검증 (0-24시간)."""
    # Given: 유효한 범위의 학습 시간
    valid_data = {
        "study_plan_id": "123e4567-e89b-12d3-a456-426614174000",
        "hours_studied": 5.5,
    }

    # When & Then: 정상 생성
    checkin = CheckinCreate(**valid_data)
    assert checkin.hours_studied == 5.5

    # Given: 음수 시간 (유효하지 않음)
    invalid_data_negative = {
        "study_plan_id": "123e4567-e89b-12d3-a456-426614174000",
        "hours_studied": -1.0,
    }

    # When & Then: ValidationError 발생
    with pytest.raises(Exception):  # Pydantic ValidationError
        CheckinCreate(**invalid_data_negative)

    # Given: 24시간 초과 (유효하지 않음)
    invalid_data_over = {
        "study_plan_id": "123e4567-e89b-12d3-a456-426614174000",
        "hours_studied": 25.0,
    }

    # When & Then: ValidationError 발생
    with pytest.raises(Exception):  # Pydantic ValidationError
        CheckinCreate(**invalid_data_over)
