"""핵심 포인트 텍스트 길이 테스트.

학습 팁 등의 텍스트가 과도하게 잘리지 않는지 검증합니다.
"""

from datetime import datetime

from app.schemas.certificate import CategoryInfo, Certificate
from app.schemas.recommendation import RecommendationRequest
from app.services.study.recommendation_service import RecommendationService


def _create_test_certificate(**kwargs):
    """테스트용 Certificate 객체 생성 헬퍼."""
    defaults = {
        "raw_id": kwargs.get("id", "test-cert"),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    return Certificate(**{**defaults, **kwargs})


def test_학습_팁이_40자_이상일_때_적절히_표시됨():
    """학습 팁이 40자 이상일 때 너무 짧게 잘리지 않아야 함."""
    # Given: 긴 학습 팁이 있는 자격증
    long_tip = "기출문제를 최소 3회 이상 반복하여 풀이하는 것이 정답률 향상에 도움이 됩니다. 특히 오답노트를 작성하여 틀린 문제를 집중 복습하세요."

    cert = _create_test_certificate(
        id="test-cert-001",
        title="정보처리기사",
        categories=[CategoryInfo(name="국가기술자격", code="QT")],
        difficulty=4,
        study_period_days=180,
        user_reviews={"study_tips": [long_tip], "difficulty_feedback": "중상"},
    )

    request = RecommendationRequest(
        purpose="취업",
        interest_domains=["IT개발"],
        study_timeline="6개월 이하",
        difficulty_preference="어려워도 상관없음",
    )

    service = RecommendationService(db=None)

    # When: 핵심 포인트 생성
    key_points = service._generate_key_points(cert, request)

    # Then: 학습 팁이 포함되어야 함
    study_tip_point = next((p for p in key_points if p.startswith("학습 팁:")), None)
    assert study_tip_point is not None, "학습 팁 포인트가 생성되어야 합니다"

    # 원본 텍스트의 앞부분이 포함되어 있어야 함
    assert "기출문제를 최소 3회 이상 반복하여" in study_tip_point

    # 너무 짧게 잘리지 않아야 함 (최소 60자 이상)
    assert (
        len(study_tip_point) >= 60
    ), f"학습 팁이 너무 짧게 잘렸습니다: {len(study_tip_point)}자"

    # 원본의 충분한 내용이 포함되어야 함 (최소 70% 이상)
    tip_content = study_tip_point.replace("학습 팁: ", "")
    # "..."가 있으면 제거하고 비교
    tip_content_clean = tip_content.rstrip("...")

    # 원본의 상당 부분이 포함되어 있는지 확인
    # 원본 텍스트의 최소 70% 이상이 포함되어야 함
    assert (
        len(tip_content_clean) >= len(long_tip) * 0.7
    ), f"학습 팁 내용이 너무 많이 잘렸습니다: {len(tip_content_clean)}자 (원본: {len(long_tip)}자)"


def test_학습_팁이_짧을_때는_전체_표시됨():
    """학습 팁이 짧을 때는 전체가 표시되어야 함."""
    # Given: 짧은 학습 팁
    short_tip = "기출문제 3회 반복"

    cert = _create_test_certificate(
        id="test-cert-002",
        title="컴퓨터활용능력 1급",
        categories=[CategoryInfo(name="국가기술자격", code="QT")],
        difficulty=2,
        study_period_days=60,
        user_reviews={"study_tips": [short_tip]},
    )

    request = RecommendationRequest(
        purpose="취업",
        interest_domains=["총무/법무/사무"],
        study_timeline="3개월 이하",
        difficulty_preference="쉬운 편",
    )

    service = RecommendationService(db=None)

    # When: 핵심 포인트 생성
    key_points = service._generate_key_points(cert, request)

    # Then: 전체 텍스트가 포함되어야 함
    study_tip_point = next((p for p in key_points if p.startswith("학습 팁:")), None)
    assert study_tip_point == f"학습 팁: {short_tip}"


def test_학습_팁이_없을_때_에러_없이_처리됨():
    """학습 팁이 없어도 에러 없이 처리되어야 함."""
    # Given: 학습 팁이 없는 자격증
    cert = _create_test_certificate(
        id="test-cert-003",
        title="네트워크관리사 2급",
        categories=[CategoryInfo(name="민간자격", code="PT")],
        difficulty=3,
        study_period_days=90,
    )

    request = RecommendationRequest(
        purpose="취업",
        interest_domains=["IT개발"],
        study_timeline="6개월 이하",
        difficulty_preference="중간",
    )

    service = RecommendationService(db=None)

    # When: 핵심 포인트 생성
    key_points = service._generate_key_points(cert, request)

    # Then: 에러 없이 처리되고, 학습 팁이 없어야 함
    assert isinstance(key_points, list)
    study_tip_points = [p for p in key_points if p.startswith("학습 팁:")]
    assert len(study_tip_points) == 0


def test_여러_학습_팁_중_첫_번째만_사용됨():
    """여러 개의 학습 팁이 있을 때 첫 번째만 사용되어야 함."""
    # Given: 여러 학습 팁이 있는 자격증
    tips = [
        "첫 번째 팁: 기출문제를 최소 3회 이상 반복하여 풀이하는 것이 정답률 향상에 도움이 됩니다.",
        "두 번째 팁: 이론 공부와 실습을 병행하세요.",
        "세 번째 팁: 스터디 그룹에 참여하면 도움이 됩니다.",
    ]

    cert = _create_test_certificate(
        id="test-cert-004",
        title="정보보안기사",
        categories=[CategoryInfo(name="국가기술자격", code="QT")],
        difficulty=4,
        study_period_days=180,
        user_reviews={"study_tips": tips},
    )

    request = RecommendationRequest(
        purpose="이직",
        interest_domains=["IT개발"],
        study_timeline="6개월 이하",
        difficulty_preference="어려워도 상관없음",
    )

    service = RecommendationService(db=None)

    # When: 핵심 포인트 생성
    key_points = service._generate_key_points(cert, request)

    # Then: 첫 번째 팁만 포함되어야 함
    study_tip_points = [p for p in key_points if p.startswith("학습 팁:")]
    assert len(study_tip_points) == 1
    assert "첫 번째 팁" in study_tip_points[0]
    assert "두 번째 팁" not in study_tip_points[0]
    assert "세 번째 팁" not in study_tip_points[0]
