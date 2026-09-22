"""학습 계획 생성 서비스(LLM 기반).

자격증 정보와 사용자 입력을 기반으로 맞춤형 학습 계획을 생성합니다.
"""

import json
from datetime import date
from typing import Any, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.core.config import get_settings


class MilestoneData(BaseModel):
    """주차별 마일스톤 데이터."""

    week: int = Field(..., description="주차")
    title: str = Field(..., description="마일스톤 제목")
    description: str = Field(..., description="마일스톤 설명")
    hours: float = Field(..., description="예상 학습 시간")
    completed: bool = Field(False, description="완료 여부")


class TopicData(BaseModel):
    """학습 주제 데이터."""

    name: str = Field(..., description="주제명")
    description: str = Field(..., description="주제 설명")
    week: int = Field(..., description="학습 주차")
    hours: float = Field(..., description="예상 학습 시간")
    priority: str = Field("medium", description="우선순위 (high/medium/low)")


class GeneratedStudyPlan(BaseModel):
    """LLM이 생성한 학습 계획 데이터."""

    milestones: list[MilestoneData] = Field(..., description="주차별 마일스톤 목록")
    topics: list[TopicData] = Field(..., description="학습 주제 목록")
    total_weeks: int = Field(..., description="총 학습 주차 수")
    estimated_total_hours: float = Field(..., description="총 예상 학습 시간")


class StudyPlanService:
    """LLM 기반 학습 계획 생성 서비스.

    OpenAI API를 사용합니다.
    """

    def __init__(self, api_key: Optional[str] = None):
        """StudyPlanService를 초기화합니다.

        Args:
            api_key: API 키. 제공되지 않으면 설정 값을 사용합니다.
        """
        settings = get_settings()

        # OpenAI API 설정 사용
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL_NAME

        # OpenAI 클라이언트 생성
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None

    async def generate_study_plan(
        self,
        certificate_data: dict[str, Any],
        target_date: date,
        daily_study_hours: float,
    ) -> GeneratedStudyPlan:
        """자격증 정보와 사용자 입력을 기반으로 학습 계획을 생성합니다.

        Args:
            certificate_data: 자격증 정보(overview, difficulty, study_period_days 등)
            target_date: 목표 완료일
            daily_study_hours: 하루 학습 시간

        Returns:
            GeneratedStudyPlan: 생성된 학습 계획(milestones, topics).

        Raises:
            ValueError: OPENAI_API_KEY가 설정되지 않았거나 LLM 응답이 비어있을 때.
        """
        if not self.client:
            raise ValueError("OPENAI_API_KEY not configured")

        # 목표일까지 남은 일수 계산
        from datetime import datetime

        today = datetime.now().date()
        days_remaining = (target_date - today).days

        if days_remaining <= 0:
            raise ValueError("목표일은 오늘보다 미래여야 합니다")

        # Certificate 정보 추출
        cert_title = certificate_data.get("title", "자격증")
        overview = certificate_data.get("overview", "")
        difficulty = certificate_data.get("difficulty", 3)
        study_period_days = certificate_data.get("study_period_days", 90)
        study_guide = certificate_data.get("study_guide", {})
        exam_info = certificate_data.get("exam_info", {})

        # 시험 과목 추출
        subjects = exam_info.get("subjects", [])
        subjects_text = ", ".join(subjects) if subjects else "정보 없음"

        # 핵심 출제 토픽 추출
        key_exam_topics = study_guide.get("key_exam_topics", [])
        key_exam_topics_text = (
            "\n".join(
                [
                    f"- {t.get('topic', '')}: {t.get('frequency', '')} / {t.get('importance', '')} - {t.get('description', '')}"
                    for t in key_exam_topics
                ]
            )
            if key_exam_topics
            else "정보 없음"
        )

        # 시간 배분 가이드 추출
        time_allocation = study_guide.get("time_allocation", {})
        time_allocation_text = (
            json.dumps(time_allocation, ensure_ascii=False, indent=2)
            if time_allocation
            else "정보 없음"
        )

        # 추천 교재 추출
        recommended_books = study_guide.get("recommended_books", [])
        books_text = (
            "\n".join(
                [
                    f"- {book.get('title', '')} ({book.get('type', '')})"
                    for book in recommended_books
                ]
            )
            if recommended_books
            else "정보 없음"
        )

        # 성공 팁 추출
        success_tips = study_guide.get("success_tips", [])
        tips_text = (
            "\n".join([f"- {tip}" for tip in success_tips])
            if success_tips
            else "정보 없음"
        )

        # System Prompt
        system_prompt = f"""당신은 자격증 합격 전문가 학습 플래너 AI입니다.
사용자가 제공한 자격증 정보, 학습 가능 기간, 일일 공부 시간, 현재 실력을 기반으로
가장 현실적이고 과학적인 주차별 스터디 계획(Milestones)을 수립해야 합니다.

자격증 정보:
- 제목: {cert_title}
- 개요: {overview}
- 난이도: {difficulty}/5
- 권장 준비 기간: {study_period_days}일
- 시험 과목: {subjects_text}

학습 가이드:
- 핵심 출제 토픽:
{key_exam_topics_text}

- 시간 배분:
{time_allocation_text}

- 추천 교재:
{books_text}

- 성공 팁:
{tips_text}

사용자 입력:
- 목표 완료일: {target_date.isoformat()} (오늘부터 {days_remaining}일 남음)
- 하루 학습 시간: {daily_study_hours}시간

학습 계획 생성 규칙:
1. **자격증 난이도 & 권장 학습 기간 반영**
   - 난이도(difficulty)와 시간 배분(time_allocation)에 맞춰 강도 조절
   - 예: difficulty 5이면 이론 40% + 실전 50% + 복습 10% 비율 준수
   - 권장 준비 기간({study_period_days}일)과 실제 가능 기간 비교해 현실적으로 조정
   - 시험 구조(필기/실기, OMR/주관식)를 반영해 학습 비중을 조정
2. **시험 과목별 학습 전략 수립**
   - exam_info.subjects 각 과목을 분석해 과목별 계획 수립
   - 이론 과목은 이론 비중, 실무 과목은 실전 비중을 높게 설정
   - 과목별 합격선/평균 합격 기준을 명시
   - 합격률 추이(pass_rate_trend)가 있으면 합격 가능성 평가에 반영
3. **학습 방법론의 과학적 적용**
   - study_guide.study_methods를 기반으로 학습 활동을 구체화
   - 기본서 1~3회독, 기출문제 1~3차, 강의 활용, 스터디 그룹, 모의고사 활용을 단계별로 반영
4. **시간 배분 최적화**
   - 총 학습 시간 = 하루 학습 시간 × 남은 일수
   - theory/practice/review 비율을 준수하고 주차별로 배분
   - 시간이 부족하면 마일스톤 기간 연장 + review 조정
   - 시간이 충분하면 심화 학습 모듈 및 과목별 심화 시간 추가
5. **핵심 출제 토픽 반영**
   - study_guide.key_exam_topics를 기반으로 주요 학습 토픽과 우선순위 결정
   - 중요도(importance)가 '상'인 토픽에 더 많은 시간 배분
   - 출제 빈도(frequency)가 높은 토픽을 우선 학습
6. **주차별 마일스톤 구체성**
   - 각 주차는 명확한 목표와 활동을 포함
   - "기출문제 3회 풀이", "모의고사 2회"처럼 실행 단위를 구체화

출력 형식 (JSON):
{{
  "milestones": [
    {{
      "week": 1,
      "title": "1주차: 기초 개념 학습",
      "description": "자격증 시험의 기본 개념과 이론을 학습합니다. 교재 1-3장을 정독하고 핵심 개념을 정리합니다.",
      "hours": 14.0,
      "completed": false
    }},
    {{
      "week": 2,
      "title": "2주차: 심화 학습 및 기출문제",
      "description": "교재 4-6장을 학습하고 기출문제 1회차를 풀이합니다. 오답노트를 작성합니다.",
      "hours": 14.0,
      "completed": false
    }}
  ],
  "topics": [
    {{
      "name": "기초 이론 학습",
      "description": "자격증 시험의 기본 이론과 개념을 학습합니다 (교재 1-3장).",
      "week": 1,
      "hours": 10.0,
      "priority": "high"
    }},
    {{
      "name": "기출문제 1회차",
      "description": "최근 3년간 기출문제를 풀이하고 오답노트를 작성합니다.",
      "week": 2,
      "hours": 8.0,
      "priority": "high"
    }}
  ],
  "total_weeks": 계산된 총 주차 수,
  "estimated_total_hours": 총 예상 학습 시간
}}

**중요**:
- milestones는 최소 3개 이상
- topics는 각 주차에 골고루 배분
- 모든 시간의 합 = 총 학습 시간과 일치
- 실제 자격증 준비에 필요한 구체적인 내용 포함
"""

        user_prompt = f"""위 자격증 정보와 사용자 입력을 바탕으로 학습 계획을 생성해주세요.

특히 다음 사항을 고려하세요:
1. 남은 기간({days_remaining}일)과 권장 준비 기간({study_period_days}일)의 차이
2. 하루 학습 시간({daily_study_hours}시간)의 현실성
3. 시험 과목({subjects_text})을 모두 커버
4. 핵심 출제 토픽 우선순위 반영
5. 시간 배분 가이드(theory/practice/review) 비율 적용

현실적이고 실행 가능한 계획을 JSON 형식으로 생성해주세요."""

        # LLM 호출
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,  # 일관성 있는 결과를 위해 낮은 temperature
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        # JSON 파싱 및 검증
        data = json.loads(content)
        return GeneratedStudyPlan(**data)


# Singleton instance
_study_plan_service: Optional[StudyPlanService] = None


def get_study_plan_service() -> StudyPlanService:
    """싱글턴 StudyPlanService 인스턴스를 반환합니다.

    Returns:
        StudyPlanService 인스턴스.
    """
    global _study_plan_service
    if _study_plan_service is None:
        _study_plan_service = StudyPlanService()
    return _study_plan_service
