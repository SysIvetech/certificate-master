"""자격증 데이터 포맷팅 유틸리티.

B4: format 함수 중복 제거 - EmbeddingService와 VectorStoreService에서 공통 사용.
B5: 사용자 매칭용 임베딩 텍스트 및 메타데이터 추가 (2026-01-29).
"""


def format_certificate_text(cert: dict) -> str:
    """임베딩 생성을 위해 자격증 데이터를 텍스트로 포맷합니다.

    의미 임베딩 생성을 위해 관련 필드를 하나의 텍스트로 결합합니다.
    섹션별로 구분하여 검색 품질을 높입니다.

    Args:
        cert: 자격증 데이터를 담은 딕셔너리.

    Returns:
        임베딩용으로 포맷된 텍스트 문자열.
    """
    # categories 배열에서 이름 추출
    categories = cert.get("categories", [])
    category_display = (
        ", ".join([cat.get("name", "") for cat in categories]) if categories else ""
    )

    parts = [
        f"자격증: {cert.get('title', '')}",
        f"분류: {category_display}",
        f"계열: {cert.get('series', '')}",
        f"개요: {cert.get('overview', '')}",
        f"난이도: {cert.get('difficulty', 'N/A')}/5",
        f"준비기간: {cert.get('study_period_days', 'N/A')}일",
    ]

    # Career info (진로 정보)
    career = cert.get("career_info", {}) or {}
    career_parts = []
    if career.get("industry"):
        industry = career["industry"]
        if isinstance(industry, list):
            career_parts.append(f"산업분야: {', '.join(industry)}")
        else:
            career_parts.append(f"산업분야: {industry}")
    if career.get("use_cases"):
        career_parts.append(f"활용분야: {', '.join(career['use_cases'])}")
    if career.get("related_jobs"):
        career_parts.append(f"관련직업: {', '.join(career['related_jobs'])}")
    if career.get("job_prospects"):
        career_parts.append(f"취업전망: {career['job_prospects']}")
    if career.get("average_salary"):
        career_parts.append(f"평균연봉: {career['average_salary']}")

    if career_parts:
        parts.append("")
        parts.append("[진로 정보]")
        parts.extend(career_parts)

    # Exam info (시험 정보)
    exam = cert.get("exam_info", {}) or {}
    exam_parts = []
    if exam.get("exam_type"):
        exam_parts.append(f"시험유형: {exam['exam_type']}")
    if exam.get("exam_structure"):
        exam_parts.append(f"시험구성: {exam['exam_structure']}")
    if exam.get("subjects"):
        subjects = exam["subjects"]
        # 딕셔너리 리스트인 경우 name 필드 추출
        if subjects and isinstance(subjects[0], dict):
            subject_names = [s.get("name", "") for s in subjects if s.get("name")]
            exam_parts.append(f"시험과목: {', '.join(subject_names)}")
        else:
            exam_parts.append(f"시험과목: {', '.join(subjects)}")
    if exam.get("passing_criteria"):
        exam_parts.append(f"합격기준: {exam['passing_criteria']}")
    if exam.get("pass_rate_trend"):
        exam_parts.append(f"합격률추이: {exam['pass_rate_trend']}")
    if exam.get("recent_trends"):
        exam_parts.append(f"최근출제동향: {exam['recent_trends']}")

    if exam_parts:
        parts.append("")
        parts.append("[시험 정보]")
        parts.extend(exam_parts)

    # User reviews (학습자 후기)
    reviews = cert.get("user_reviews", {}) or {}
    review_parts = []
    if reviews.get("difficulty_feedback"):
        review_parts.append(f"난이도피드백: {reviews['difficulty_feedback']}")
    if reviews.get("summary"):
        review_parts.append(f"후기요약: {reviews['summary']}")
    if reviews.get("study_tips"):
        tips = reviews["study_tips"][:2]  # 상위 2개
        review_parts.append(f"학습팁: {' / '.join(tips)}")

    if review_parts:
        parts.append("")
        parts.append("[학습자 후기]")
        parts.extend(review_parts)

    # Study guide (학습 가이드)
    guide = cert.get("study_guide", {}) or {}
    guide_parts = []
    if guide.get("study_methods"):
        methods = guide["study_methods"][:2]  # 상위 2개
        guide_parts.append(f"학습방법: {' / '.join(methods)}")
    if guide.get("success_tips"):
        tips = guide["success_tips"][:3]  # 상위 3개
        guide_parts.append(f"성공팁: {' / '.join(tips)}")

    if guide_parts:
        parts.append("")
        parts.append("[학습 가이드]")
        parts.extend(guide_parts)

    # ============================================================
    # 취업준비생 관점 정보 (NEW: 2026-01-28)
    # ============================================================

    # Job market info (채용 시장 정보)
    job_market = cert.get("job_market_info", {}) or {}
    job_market_parts = []
    if job_market.get("job_posting_frequency"):
        job_market_parts.append(f"채용공고빈도: {job_market['job_posting_frequency']}")
    if job_market.get("preferred_industries"):
        job_market_parts.append(
            f"선호산업군: {', '.join(job_market['preferred_industries'][:5])}"
        )
    if job_market.get("preferred_companies"):
        job_market_parts.append(
            f"우대기업: {', '.join(job_market['preferred_companies'][:5])}"
        )
    if job_market.get("requirement_type"):
        job_market_parts.append(f"채용요건유형: {job_market['requirement_type']}")
    if job_market.get("public_sector_points"):
        job_market_parts.append(f"공공부문가산점: {job_market['public_sector_points']}")
    if job_market.get("salary_premium"):
        job_market_parts.append(f"연봉가산효과: {job_market['salary_premium']}")

    if job_market_parts:
        parts.append("")
        parts.append("[채용 시장 정보]")
        parts.extend(job_market_parts)

    # Cost breakdown (비용 정보)
    cost = cert.get("cost_breakdown", {}) or {}
    cost_parts = []
    if cost.get("exam_fee"):
        cost_parts.append(f"응시료: {cost['exam_fee']}")
    if cost.get("total_estimated_cost"):
        cost_parts.append(f"총예상비용: {cost['total_estimated_cost']}")
    if cost.get("free_resources"):
        cost_parts.append(f"무료자료: {', '.join(cost['free_resources'][:3])}")

    if cost_parts:
        parts.append("")
        parts.append("[비용 정보]")
        parts.extend(cost_parts)

    # Feasibility info (합격 가능성 정보)
    feasibility = cert.get("feasibility_info", {}) or {}
    feasibility_parts = []
    if feasibility.get("non_major_pass_rate"):
        feasibility_parts.append(
            f"비전공자합격률: {feasibility['non_major_pass_rate']}"
        )
    if feasibility.get("self_study_possible") is not None:
        feasibility_parts.append(
            f"독학가능: {'가능' if feasibility['self_study_possible'] else '어려움'}"
        )
    if feasibility.get("minimum_study_period"):
        feasibility_parts.append(
            f"최소준비기간: {feasibility['minimum_study_period']}일"
        )
    if feasibility.get("working_adult_tips"):
        tips = feasibility["working_adult_tips"][:2]
        feasibility_parts.append(f"직장인팁: {' / '.join(tips)}")

    if feasibility_parts:
        parts.append("")
        parts.append("[합격 가능성 정보]")
        parts.extend(feasibility_parts)

    # Similar certificates (유사 자격증)
    similar = cert.get("similar_certificates", []) or []
    if similar:
        parts.append("")
        parts.append("[유사 자격증]")
        for sim in similar[:3]:  # 최대 3개
            if sim.get("title"):
                comparison = sim.get("comparison", "")
                parts.append(f"- {sim['title']}: {comparison}")

    # ============================================================
    # 사용자 매칭 정보 통합 (NEW: 2026-01-29)
    # ============================================================
    user_matching_text = _build_user_matching_section(cert)
    if user_matching_text:
        parts.append("")
        parts.append(user_matching_text)

    return "\n".join(parts)


def _build_user_matching_section(cert: dict) -> str:
    """사용자 매칭용 섹션을 생성합니다 (format_certificate_text 내부용).

    Args:
        cert: 자격증 데이터.

    Returns:
        사용자 매칭 섹션 텍스트.
    """
    parts = []

    parts.append("[추천 대상]")

    # 비전공자 정보
    feasibility = cert.get("feasibility_info", {}) or {}
    if feasibility.get("self_study_possible"):
        parts.append("비전공자: 독학 가능, 비전공자도 도전하기 좋음")
    elif feasibility.get("non_major_pass_rate"):
        parts.append(f"비전공자 합격률: {feasibility['non_major_pass_rate']}")

    # 직장인 정보
    if feasibility.get("working_adult_tips"):
        tips = feasibility["working_adult_tips"][:2]
        parts.append(f"직장인 학습팁: {' / '.join(tips)}")

    # CBT/시험 형태
    schedule = cert.get("exam_schedule_detail", {}) or {}
    if schedule.get("cbt_available"):
        parts.append("CBT 가능: 상시시험으로 일정 조율 용이")

    return "\n".join(parts) if len(parts) > 1 else ""


def build_certificate_metadata(cert: dict) -> dict:
    """ChromaDB 저장용 메타데이터를 빌드합니다.

    Args:
        cert: 자격증 데이터를 담은 딕셔너리.

    Returns:
        메타데이터 딕셔너리.
    """
    career = cert.get("career_info", {}) or {}
    exam = cert.get("exam_info", {}) or {}

    # industry 처리
    industry = career.get("industry", [])
    if isinstance(industry, list):
        industry_str = ", ".join(industry)
    else:
        industry_str = industry or ""

    # categories 배열에서 이름 추출
    categories = cert.get("categories", [])
    categories_str = (
        ", ".join([cat.get("name", "") for cat in categories]) if categories else ""
    )

    # 취업준비생 관점 필드 처리 (NEW: 2026-01-28)
    job_market = cert.get("job_market_info", {}) or {}
    cost = cert.get("cost_breakdown", {}) or {}
    feasibility = cert.get("feasibility_info", {}) or {}
    schedule = cert.get("exam_schedule_detail", {}) or {}
    similar = cert.get("similar_certificates", []) or []

    # preferred_industries 처리
    preferred_industries = job_market.get("preferred_industries", [])
    if isinstance(preferred_industries, list):
        preferred_industries_str = ", ".join(preferred_industries[:5])
    else:
        preferred_industries_str = ""

    # preferred_companies 처리
    preferred_companies = job_market.get("preferred_companies", [])
    if isinstance(preferred_companies, list):
        preferred_companies_str = ", ".join(preferred_companies[:5])
    else:
        preferred_companies_str = ""

    # similar_certificates 처리
    similar_titles = [s.get("title", "") for s in similar[:3] if s.get("title")]
    similar_certificates_str = ", ".join(similar_titles)

    # 목표 직종/기업 타입 (사용자 매칭용)
    related_jobs = career.get("related_jobs", [])
    target_job_types = ", ".join(related_jobs[:5]) if related_jobs else ""
    target_company_types = (
        ", ".join(preferred_industries[:5]) if preferred_industries else ""
    )

    return {
        "title": cert.get("title", ""),
        "categories": categories_str,
        "series": cert.get("series", "") or "",
        "difficulty": cert.get("difficulty"),
        "study_period_days": cert.get("study_period_days"),
        "overview": (cert.get("overview", "") or "")[:500],
        "industry": industry_str[:200],
        "average_salary": (career.get("average_salary", "") or "")[:100],
        "exam_type": (exam.get("exam_type", "") or "")[:100],
        # 취업준비생 관점 필드 (NEW: 2026-01-28)
        "job_posting_frequency": job_market.get("job_posting_frequency", "") or "",
        "preferred_industries": preferred_industries_str[:200],
        "preferred_companies": preferred_companies_str[:200],
        "requirement_type": job_market.get("requirement_type", "") or "",
        "public_sector_points": (job_market.get("public_sector_points", "") or "")[
            :100
        ],
        "salary_premium": (job_market.get("salary_premium", "") or "")[:100],
        "total_estimated_cost": (cost.get("total_estimated_cost", "") or "")[:100],
        "self_study_possible": feasibility.get("self_study_possible"),
        "non_major_pass_rate": (feasibility.get("non_major_pass_rate", "") or "")[:50],
        "minimum_study_period": feasibility.get("minimum_study_period"),
        "cbt_available": schedule.get("cbt_available"),
        "annual_exam_count": schedule.get("annual_exam_count"),
        "similar_certificates": similar_certificates_str[:200],
        # 사용자 매칭용 필드 (NEW: 2026-01-29)
        "non_major_friendly": _is_non_major_friendly(cert),
        "working_adult_friendly": _is_working_adult_friendly(cert),
        "budget_category": _calculate_budget_category(cert),
        "weekly_hours_required": _calculate_weekly_hours_required(cert),
        "target_job_types": target_job_types[:200],
        "target_company_types": target_company_types[:200],
        # 도메인 분류 (NEW)
        "domain": cert.get("domain", "") or "",
    }


# ============================================================
# 사용자 매칭용 임베딩 텍스트/메타데이터 (NEW: 2026-01-29)
# ============================================================


def _calculate_weekly_hours_required(cert: dict) -> float:
    """주당 필요 학습 시간을 계산합니다.

    Args:
        cert: 자격증 데이터.

    Returns:
        주당 필요 학습 시간 (시간 단위).
    """
    study_days = cert.get("study_period_days")
    difficulty = cert.get("difficulty")
    if difficulty is None:
        difficulty = 3

    if not study_days:
        # 기본값: 난이도 기반 추정
        return difficulty * 5  # 난이도 3이면 주 15시간

    # 하루 평균 2시간 기준으로 계산
    # 난이도가 높을수록 하루 학습 시간 증가
    daily_hours = 1.5 + (difficulty * 0.5)  # 난이도 3이면 하루 3시간
    total_hours = study_days * daily_hours
    weeks = study_days / 7

    if weeks < 1:
        weeks = 1

    return round(total_hours / weeks, 1)


def _calculate_budget_category(cert: dict) -> str:
    """예산 범주를 계산합니다.

    Args:
        cert: 자격증 데이터.

    Returns:
        예산 범주: "low", "medium", "high"
    """
    cost = cert.get("cost_breakdown", {}) or {}
    total_cost_str = cost.get("total_estimated_cost", "")

    if not total_cost_str:
        # 난이도 기반 추정
        difficulty = cert.get("difficulty")
        if difficulty is None:
            difficulty = 3
        if difficulty <= 2:
            return "low"
        elif difficulty <= 4:
            return "medium"
        return "high"

    # 숫자 추출 (예: "30-50만원" -> 50)
    import re

    numbers = re.findall(r"\d+", total_cost_str)
    if numbers:
        max_cost = max(int(n) for n in numbers)
        # 단위가 만원인 경우
        if "만원" in total_cost_str or "만" in total_cost_str:
            if max_cost <= 20:
                return "low"
            elif max_cost <= 50:
                return "medium"
            return "high"

    return "medium"  # 기본값


def _is_non_major_friendly(cert: dict) -> bool:
    """비전공자 친화도를 판단합니다.

    Args:
        cert: 자격증 데이터.

    Returns:
        비전공자 친화 여부.
    """
    feasibility = cert.get("feasibility_info", {}) or {}

    # 독학 가능 여부
    self_study = feasibility.get("self_study_possible")
    if self_study is True:
        return True

    # 비전공자 합격률 분석
    non_major_rate = feasibility.get("non_major_pass_rate", "")
    if non_major_rate:
        import re

        numbers = re.findall(r"\d+", non_major_rate)
        if numbers:
            rate = int(numbers[0])
            if rate >= 30:  # 30% 이상이면 비전공자 친화적
                return True

    # 난이도 기반 (낮으면 비전공자 친화적)
    difficulty = cert.get("difficulty")
    if difficulty is not None and difficulty <= 2:
        return True

    return False


def _is_working_adult_friendly(cert: dict) -> bool:
    """직장인 친화도를 판단합니다.

    Args:
        cert: 자격증 데이터.

    Returns:
        직장인 친화 여부.
    """
    feasibility = cert.get("feasibility_info", {}) or {}

    # 직장인 팁이 있으면 친화적
    working_tips = feasibility.get("working_adult_tips", [])
    if working_tips and len(working_tips) >= 2:
        return True

    # CBT 가능 여부 (시험 시간 유연)
    schedule = cert.get("exam_schedule_detail", {}) or {}
    if schedule.get("cbt_available"):
        return True

    # 최소 준비 기간이 짧으면 친화적
    min_period = feasibility.get("minimum_study_period")
    if min_period and min_period <= 60:
        return True

    # 연간 시험 횟수가 많으면 친화적
    exam_count = schedule.get("annual_exam_count")
    if exam_count and exam_count >= 4:
        return True

    return False


def format_user_matching_text(cert: dict) -> str:
    """사용자 매칭을 위한 임베딩 텍스트를 생성합니다.

    사용자가 입력하는 조건(비전공자, 직장인, 예산, 학습시간 등)과
    매칭될 수 있도록 최적화된 텍스트를 생성합니다.

    Args:
        cert: 자격증 데이터를 담은 딕셔너리.

    Returns:
        사용자 매칭용으로 포맷된 텍스트 문자열.
    """
    parts = []

    # 기본 정보
    parts.append(f"자격증: {cert.get('title', '')}")

    # ============================================================
    # [추천 대상] 섹션 - 사용자 프로필 매칭
    # ============================================================
    parts.append("")
    parts.append("[추천 대상]")

    # 비전공자 추천 여부
    if _is_non_major_friendly(cert):
        parts.append("비전공자 추천: 비전공자도 독학으로 합격 가능한 자격증입니다.")
        feasibility = cert.get("feasibility_info", {}) or {}
        non_major_rate = feasibility.get("non_major_pass_rate", "")
        if non_major_rate:
            parts.append(f"비전공자 합격률: {non_major_rate}")
    else:
        parts.append("비전공자: 전공 지식이 필요할 수 있어 추가 학습이 필요합니다.")

    # 직장인 추천 여부
    if _is_working_adult_friendly(cert):
        parts.append("직장인 추천: 직장인이 준비하기 좋은 자격증입니다.")
        feasibility = cert.get("feasibility_info", {}) or {}
        tips = feasibility.get("working_adult_tips", [])
        if tips:
            parts.append(f"직장인 팁: {' / '.join(tips[:2])}")
    else:
        parts.append("직장인: 충분한 학습 시간 확보가 필요합니다.")

    # ============================================================
    # 예산/비용 정보
    # ============================================================
    cost = cert.get("cost_breakdown", {}) or {}
    budget_category = _calculate_budget_category(cert)
    budget_labels = {
        "low": "저렴 (20만원 이하)",
        "medium": "보통 (20-50만원)",
        "high": "고비용 (50만원 이상)",
    }

    parts.append(f"예산 범위: {budget_labels.get(budget_category, '보통')}")
    if cost.get("total_estimated_cost"):
        parts.append(f"총 비용 예상: {cost['total_estimated_cost']}")
    if cost.get("free_resources"):
        parts.append(f"무료 학습 자료: {', '.join(cost['free_resources'][:3])}")

    # ============================================================
    # 학습 시간 요구량
    # ============================================================
    weekly_hours = _calculate_weekly_hours_required(cert)
    parts.append(f"학습 시간 요구량: 주 {weekly_hours}시간 권장")

    study_days = cert.get("study_period_days")
    if study_days:
        parts.append(f"공부 시간: 약 {study_days}일 ({study_days // 7}주) 준비 필요")

    # ============================================================
    # 시험 형태
    # ============================================================
    exam = cert.get("exam_info", {}) or {}
    schedule = cert.get("exam_schedule_detail", {}) or {}

    exam_format_parts = []
    if exam.get("exam_type"):
        exam_format_parts.append(exam["exam_type"])
    if schedule.get("cbt_available"):
        exam_format_parts.append("CBT 가능 (상시시험)")
    else:
        exam_format_parts.append("정기시험")

    if exam_format_parts:
        parts.append(f"시험 형태: {', '.join(exam_format_parts)}")

    if schedule.get("annual_exam_count"):
        parts.append(f"연간 시험 횟수: {schedule['annual_exam_count']}회")

    # ============================================================
    # [목표 직종] 섹션 - 진로 매칭
    # ============================================================
    career = cert.get("career_info", {}) or {}
    job_market = cert.get("job_market_info", {}) or {}

    parts.append("")
    parts.append("[목표 직종]")

    if career.get("related_jobs"):
        parts.append(f"관련 직업: {', '.join(career['related_jobs'][:5])}")
    if career.get("use_cases"):
        parts.append(f"활용 분야: {', '.join(career['use_cases'][:5])}")
    if career.get("industry"):
        industry = career["industry"]
        if isinstance(industry, list):
            parts.append(f"산업 분야: {', '.join(industry[:5])}")
        else:
            parts.append(f"산업 분야: {industry}")

    # ============================================================
    # 기업/취업 정보
    # ============================================================
    if job_market.get("preferred_industries"):
        parts.append(
            f"선호 기업 유형: {', '.join(job_market['preferred_industries'][:5])}"
        )
    if job_market.get("preferred_companies"):
        parts.append(
            f"우대 기업 예시: {', '.join(job_market['preferred_companies'][:5])}"
        )
    if job_market.get("requirement_type"):
        parts.append(f"채용 시 요구 수준: {job_market['requirement_type']}")
    if job_market.get("public_sector_points"):
        parts.append(f"공공기관/공무원 가산점: {job_market['public_sector_points']}")

    return "\n".join(parts)


def build_user_matching_metadata(cert: dict) -> dict:
    """사용자 매칭을 위한 ChromaDB 메타데이터를 생성합니다.

    필터링에 사용할 수 있는 구조화된 메타데이터를 생성합니다.

    Args:
        cert: 자격증 데이터를 담은 딕셔너리.

    Returns:
        메타데이터 딕셔너리.
    """
    career = cert.get("career_info", {}) or {}
    job_market = cert.get("job_market_info", {}) or {}
    schedule = cert.get("exam_schedule_detail", {}) or {}

    # 목표 직종 타입 (문자열로 결합)
    related_jobs = career.get("related_jobs", [])
    target_job_types = ", ".join(related_jobs[:5]) if related_jobs else ""

    # 목표 기업 타입 (문자열로 결합)
    preferred_industries = job_market.get("preferred_industries", [])
    target_company_types = (
        ", ".join(preferred_industries[:5]) if preferred_industries else ""
    )

    return {
        # 사용자 프로필 매칭
        "non_major_friendly": _is_non_major_friendly(cert),
        "working_adult_friendly": _is_working_adult_friendly(cert),
        # 예산/시간 제약
        "budget_category": _calculate_budget_category(cert),
        "weekly_hours_required": _calculate_weekly_hours_required(cert),
        # 시험 형태
        "cbt_available": schedule.get("cbt_available"),
        # 목표 직종/기업
        "target_job_types": target_job_types[:200],
        "target_company_types": target_company_types[:200],
    }


def format_search_text(cert: dict) -> str:
    """검색 최적화용 압축 텍스트를 생성한다 (임베딩용).

    기존 format_certificate_text()가 모든 섹션을 포함하여 의미 신호가
    희석되는 문제를 해결하기 위해, 핵심 정보만 포함한 압축 텍스트를 생성한다.

    Args:
        cert: 자격증 데이터 딕셔너리

    Returns:
        검색 최적화된 압축 텍스트
    """
    career_info = cert.get("career_info", {}) or {}
    job_market_info = cert.get("job_market_info", {}) or {}

    # categories: [{code, name}] 리스트 → 이름만 추출
    categories = cert.get("categories", [])
    if isinstance(categories, list):
        categories_str = ", ".join(
            cat.get("name", "") if isinstance(cat, dict) else str(cat)
            for cat in categories
        )
    else:
        categories_str = str(categories) if categories else ""

    # industry: 리스트 또는 문자열
    industry = career_info.get("industry", "")
    if isinstance(industry, list):
        industry_str = ", ".join(industry)
    else:
        industry_str = industry or ""

    # related_jobs: 리스트
    related_jobs = career_info.get("related_jobs", [])
    if isinstance(related_jobs, list):
        related_jobs_str = ", ".join(related_jobs)
    else:
        related_jobs_str = str(related_jobs) if related_jobs else ""

    # preferred_industries: 리스트
    preferred_industries = job_market_info.get("preferred_industries", [])
    if isinstance(preferred_industries, list):
        preferred_industries_str = ", ".join(preferred_industries[:5])
    else:
        preferred_industries_str = (
            str(preferred_industries) if preferred_industries else ""
        )

    parts = [
        cert.get("title", ""),
        categories_str,
        cert.get("series", "") or "",
        industry_str,
        related_jobs_str,
        (cert.get("overview", "") or "")[:200],
        preferred_industries_str,
    ]
    return " ".join(filter(None, parts))


def build_contextual_prefix(cert: dict) -> str:
    """자격증의 Contextual Retrieval용 맥락 설명을 생성합니다.

    Anthropic Contextual Retrieval 전략에 따라, 임베딩 텍스트 앞에
    붙여서 검색 시 쿼리와의 의미적 매칭을 향상시킵니다.

    Args:
        cert: 자격증 데이터 딕셔너리.

    Returns:
        50-100 토큰의 맥락 설명 문자열.
    """
    feasibility = cert.get("feasibility_info", {}) or {}
    career = cert.get("career_info", {}) or {}
    job_market = cert.get("job_market_info", {}) or {}

    # 1. 대상 사용자
    target_users = []
    if feasibility.get("self_study_possible"):
        target_users.append("비전공자")
    difficulty = cert.get("difficulty")
    if difficulty is not None and difficulty <= 2:
        target_users.append("입문자")
    if _is_working_adult_friendly(cert):
        target_users.append("직장인")
    target = "·".join(target_users) if target_users else "관련 전공자"

    # 2. 목적
    purpose = "자기계발"
    if job_market.get("requirement_type") == "필수":
        purpose = "취업·이직 필수"
    elif job_market.get("job_posting_frequency") in ("많음", "매우 많음"):
        purpose = "취업·이직 우대"

    # 3. 기간
    days = cert.get("study_period_days") or 90
    period = f"{days // 30}개월" if days >= 30 else f"{days}일"

    # 4. 분야
    industry = career.get("industry", [])
    if isinstance(industry, list) and industry:
        domain = ", ".join(industry[:3])
    else:
        domain = cert.get("domain", "") or ""

    # 5. 계열
    series = cert.get("series", "") or ""

    # 6. 난이도
    diff = cert.get("difficulty") or 3

    return (
        f"이 자격증은 {domain} 분야, {series} 계열이며, "
        f"{target}에게 적합하며 {purpose}에 도움이 됩니다. "
        f"약 {period} 준비, 난이도 {diff}/5입니다."
    )


def format_contextual_search_text(cert: dict) -> str:
    """Contextual Retrieval용 검색 최적화 임베딩 텍스트를 생성합니다.

    기존 format_search_text()와 다른 점:
    1. Contextual Prefix가 앞에 붙어 맥락 정보 제공
    2. overview 제거 (신호 희석 방지)
    3. User Matching 태그 추가 (비전공자, 직장인, 독학가능 등)

    Args:
        cert: 자격증 데이터 딕셔너리.

    Returns:
        Contextual Prefix가 포함된 검색 최적화 텍스트.
    """
    prefix = build_contextual_prefix(cert)

    career_info = cert.get("career_info", {}) or {}
    job_market_info = cert.get("job_market_info", {}) or {}

    # categories
    categories = cert.get("categories", [])
    if isinstance(categories, list):
        categories_str = ", ".join(
            cat.get("name", "") if isinstance(cat, dict) else str(cat)
            for cat in categories
        )
    else:
        categories_str = str(categories) if categories else ""

    # industry
    industry = career_info.get("industry", "")
    if isinstance(industry, list):
        industry_str = ", ".join(industry)
    else:
        industry_str = industry or ""

    # related_jobs
    related_jobs = career_info.get("related_jobs", [])
    if isinstance(related_jobs, list):
        related_jobs_str = ", ".join(related_jobs)
    else:
        related_jobs_str = str(related_jobs) if related_jobs else ""

    # use_cases
    use_cases = career_info.get("use_cases", [])
    if isinstance(use_cases, list):
        use_cases_str = ", ".join(use_cases[:5])
    else:
        use_cases_str = str(use_cases) if use_cases else ""

    # preferred_industries
    preferred = job_market_info.get("preferred_industries", [])
    if isinstance(preferred, list):
        preferred_str = ", ".join(preferred[:5])
    else:
        preferred_str = str(preferred) if preferred else ""

    # User Matching Tags
    matching_tags = []
    if cert.get("feasibility_info", {}) and cert["feasibility_info"].get(
        "self_study_possible"
    ):
        matching_tags.append("독학가능")
    if _is_non_major_friendly(cert):
        matching_tags.append("비전공자추천")
    if _is_working_adult_friendly(cert):
        matching_tags.append("직장인추천")
    matching_str = " ".join(matching_tags)

    parts = [
        prefix,
        cert.get("title", ""),
        categories_str,
        cert.get("series", "") or "",
        industry_str,
        related_jobs_str,
        use_cases_str,
        preferred_str,
        matching_str,
    ]
    return " ".join(filter(None, parts))
