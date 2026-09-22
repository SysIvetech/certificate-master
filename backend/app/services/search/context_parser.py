"""개선된 4단계 규칙 기반 컨텍스트 파서.

기존 app.services.study.context_parser 대비 개선:
1단계: 정규식 패턴 매칭 (더 정교한 패턴)
2단계: 동시 출현어 분석 (맥락 파악)
3단계: 수치 추출 (시간, 기간)
4단계: 도메인 자동 추론 (입력 텍스트에서 도메인 키워드 매칭)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.schemas.recommendation import StructuredUserContext

logger = logging.getLogger(__name__)


# 4단계 도메인 자동 추론용 키워드 매핑
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "IT/소프트웨어": [
        "정보처리",
        "네트워크",
        "보안",
        "프로그래밍",
        "컴퓨터",
        "IT",
        "소프트웨어",
        "데이터",
        "웹",
        "앱",
        "코딩",
        "리눅스",
        "클라우드",
        "AI",
        "인공지능",
    ],
    "전기/전자": [
        "전기",
        "전자",
        "전력",
        "회로",
        "반도체",
        "통신",
    ],
    "건설/안전": [
        "건축",
        "토목",
        "건설",
        "안전",
        "소방",
        "설비",
        "측량",
        "조경",
        "시공",
    ],
    "기계/자동차": [
        "기계",
        "자동차",
        "용접",
        "금속",
        "설계",
        "CAD",
    ],
    "화학/환경": [
        "화학",
        "환경",
        "위험물",
        "에너지",
        "가스",
        "수질",
    ],
    "금융/회계": [
        "금융",
        "회계",
        "세무",
        "재무",
        "은행",
        "보험",
        "투자",
        "증권",
        "펀드",
    ],
    "의료/보건": [
        "의료",
        "보건",
        "간호",
        "약사",
        "위생",
        "요양",
    ],
    "안전/품질": [
        "산업안전",
        "품질",
        "비파괴",
        "검사",
    ],
    "식품/조리": [
        "식품",
        "조리",
        "제과",
        "제빵",
        "영양",
        "위생사",
    ],
    "디자인/미디어": [
        "디자인",
        "그래픽",
        "영상",
        "미디어",
        "컬러리스트",
    ],
    "경영/사무": [
        "경영",
        "사무",
        "물류",
        "유통",
        "무역",
        "ERP",
        "비서",
        "행정",
    ],
    "기타": [],
}

# 도메인 → 산업 키워드 매핑 (preferred_industries 생성용)
DOMAIN_TO_INDUSTRIES: dict[str, list[str]] = {
    "IT/소프트웨어": ["IT", "소프트웨어", "인터넷"],
    "전기/전자": ["전기", "전자", "반도체"],
    "건설/안전": ["건설", "건축", "토목"],
    "기계/자동차": ["기계", "자동차", "제조"],
    "화학/환경": ["화학", "환경", "에너지"],
    "금융/회계": ["금융", "회계", "보험"],
    "의료/보건": ["의료", "보건", "제약"],
    "안전/품질": ["안전", "품질관리"],
    "식품/조리": ["식품", "외식", "호텔"],
    "디자인/미디어": ["디자인", "미디어", "광고"],
    "경영/사무": ["경영", "유통", "물류"],
}


class EnhancedContextParser:
    """4단계 파이프라인으로 사용자 컨텍스트를 추출한다."""

    # 1단계: 정규식 패턴 매칭
    GOAL_PATTERNS: dict[str, list[str]] = {
        "취업": [
            r"취업|취직|입사|신입|공채|면접",
            r"졸업\s*(후|예정|하고)",
        ],
        "이직": [r"이직|전직|경력\s*전환|다른\s*직장"],
        "전문성 강화": [r"승진|연봉|경력\s*개발|스펙|전문성"],
        "개인 관심": [r"자기\s*계발|취미|관심|배우고|재미"],
        "창업": [r"창업|사업|프리랜서|독립"],
    }

    EMPLOYMENT_PATTERNS: dict[str, list[str]] = {
        "학생": [r"대학생|학생|재학|졸업\s*예정|학교"],
        "재직 중": [r"직장|재직|회사|근무|사원|주말에만|퇴근\s*후|직장인"],
        "구직 중": [r"구직|실업|무직|백수|쉬고\s*있"],
    }

    MAJOR_PATTERNS: dict[str, list[str]] = {
        "비전공자": [r"비전공|비\s*전공|타\s*전공|문과"],
        "전공자": [r"전공이|전공자|관련\s*학과|관련\s*전공"],
        "관련 경험 있음": [r"경험\s*있|경력\s*있|현장\s*경험|실무\s*경험"],
    }

    DIFFICULTY_PATTERNS: dict[str, list[str]] = {
        "하": [r"쉬운|쉽게|기초|입문|초보"],
        "중하": [r"비교적\s*쉬운|난이도\s*낮"],
        "중상": [r"도전|심화|기사급"],
        "상": [r"어려운|어렵더라도|고난이도|전문적|기술사"],
    }

    # 3단계: 수치 추출 패턴
    DAILY_HOURS_PATTERN = re.compile(r"하루\s*(\d+)\s*시간")
    WEEKLY_HOURS_PATTERN = re.compile(r"주\s*(\d+)\s*시간")
    MONTHS_PATTERN = re.compile(r"(\d+)\s*개월")
    YEAR_PATTERN = re.compile(r"(\d+)\s*년")
    SHORT_TERM_PATTERN = re.compile(r"단기|빨리|빠르게|급하게")
    WEEKEND_PATTERN = re.compile(r"주말|토요일|일요일")

    def parse(
        self,
        user_input: str,
        domains: Optional[list[str]] = None,
    ) -> StructuredUserContext:
        """사용자 입력에서 구조화된 컨텍스트를 추출한다.

        Args:
            user_input: 사용자 자연어 입력
            domains: 선택된 도메인 리스트 (선택적)

        Returns:
            추출된 StructuredUserContext
        """
        text = user_input.strip()

        # 1단계: 정규식 패턴 매칭
        goal = self._match_first(text, self.GOAL_PATTERNS, default="취업")
        employment = self._match_first(
            text, self.EMPLOYMENT_PATTERNS, default="구직 중"
        )
        major = self._match_first(text, self.MAJOR_PATTERNS, default="비전공자")
        difficulty = self._match_first(text, self.DIFFICULTY_PATTERNS, default="중")

        # 2단계: 동시 출현어 분석
        if self.WEEKEND_PATTERN.search(text) and employment == "재직 중":
            # 주말만 공부 가능 → 시간 제한
            weekly_hours_hint = 10
        else:
            weekly_hours_hint = None

        # 3단계: 수치 추출
        weekly_hours = self._extract_weekly_hours(text, employment, weekly_hours_hint)
        study_period = self._extract_study_period(text)

        # 4단계: 도메인 자동 추론
        industries = self._infer_industries(text, domains)

        return StructuredUserContext(
            goal=goal,
            employment_status=employment,
            major_background=major,
            weekly_study_hours=weekly_hours,
            max_study_period_days=study_period,
            difficulty_preference=difficulty,
            preferred_industries=industries,
        )

    def _match_first(
        self,
        text: str,
        patterns: dict[str, list[str]],
        default: str,
    ) -> str:
        """패턴 딕셔너리에서 첫 번째 매칭된 키를 반환한다."""
        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, text):
                    return key
        return default

    def _extract_weekly_hours(
        self,
        text: str,
        employment: str,
        hint: Optional[int],
    ) -> int:
        """주당 학습 시간을 추출한다."""
        # 하루 N시간 패턴
        m = self.DAILY_HOURS_PATTERN.search(text)
        if m:
            return min(int(m.group(1)) * 7, 40)

        # 주 N시간 패턴
        m = self.WEEKLY_HOURS_PATTERN.search(text)
        if m:
            return min(int(m.group(1)), 40)

        # 동시 출현어 힌트
        if hint is not None:
            return hint

        # 디폴트: 고용상태별
        defaults = {"재직 중": 10, "학생": 20, "구직 중": 15}
        return defaults.get(employment, 15)

    def _extract_study_period(self, text: str) -> int:
        """학습 기간(일)을 추출한다."""
        # N개월 패턴
        m = self.MONTHS_PATTERN.search(text)
        if m:
            return min(int(m.group(1)) * 30, 730)

        # N년 패턴
        m = self.YEAR_PATTERN.search(text)
        if m:
            return min(int(m.group(1)) * 365, 730)

        # 단기 패턴
        if self.SHORT_TERM_PATTERN.search(text):
            return 90

        # 디폴트
        return 180

    def _infer_industries(
        self,
        text: str,
        domains: Optional[list[str]],
    ) -> list[str]:
        """텍스트와 도메인에서 산업 키워드를 추론한다."""
        industries: list[str] = []

        # 명시적 도메인이 있으면 우선 사용
        if domains:
            for domain in domains:
                if domain in DOMAIN_TO_INDUSTRIES:
                    industries.extend(DOMAIN_TO_INDUSTRIES[domain])

        # 텍스트에서 도메인 키워드 매칭
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text and domain in DOMAIN_TO_INDUSTRIES:
                    for ind in DOMAIN_TO_INDUSTRIES[domain]:
                        if ind not in industries:
                            industries.append(ind)
                    break  # 해당 도메인은 한 번만

        # 최대 5개
        return industries[:5] if industries else ["IT"]
