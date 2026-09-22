"""데이터 기반 동적 템플릿 이유 생성 엔진.

자격증 메타데이터와 사용자 컨텍스트를 분석하여
맞춤형 추천 이유를 생성합니다.
"""

from dataclasses import dataclass

from app.schemas.recommendation import StructuredUserContext


@dataclass
class StrengthResult:
    """강점 분석 결과."""

    name: str
    score: float
    sentence: str


class ReasonTemplateEngine:
    """데이터 기반 동적 추천 이유 생성 엔진.

    자격증의 메타데이터에서 강점을 분석하고,
    사용자 컨텍스트에 맞춰 점수를 조정한 뒤,
    상위 강점들을 자연어 문장으로 조합합니다.
    """

    def generate(self, cert: dict, context: StructuredUserContext) -> str:
        """자격증과 사용자 컨텍스트를 기반으로 추천 이유를 생성한다.

        Args:
            cert: 자격증 메타데이터 딕셔너리
            context: 사용자의 구조화된 컨텍스트

        Returns:
            2-3문장, 50-300자의 추천 이유 문자열
        """
        analyzers = [
            self._job_market_strength,
            self._salary_strength,
            self._non_major_strength,
            self._worker_friendly_strength,
            self._cost_efficiency_strength,
            self._public_sector_strength,
            self._feasibility_strength,
        ]

        strengths: list[StrengthResult] = []
        for analyzer in analyzers:
            result = analyzer(cert, context)
            if result is not None:
                strengths.append(result)

        strengths.sort(key=lambda s: s.score, reverse=True)
        top_strengths = strengths[:3]

        if not top_strengths:
            return self._fallback_reason(cert, context)

        sentences = [s.sentence for s in top_strengths]
        reason = " ".join(sentences)

        if len(reason) > 300:
            reason = " ".join(sentences[:2])

        if len(reason) < 50:
            fallback = self._fallback_reason(cert, context)
            reason = f"{reason} {fallback}"
            if len(reason) > 300:
                reason = reason[:297] + "..."

        return reason

    def _job_market_strength(
        self, cert: dict, context: StructuredUserContext
    ) -> StrengthResult | None:
        """채용 시장 수요 강점 분석."""
        job_market = cert.get("job_market_info", {})
        if not job_market:
            return None

        freq = job_market.get("job_posting_frequency", "")
        companies = job_market.get("preferred_companies", "")
        req_type = job_market.get("requirement_type", "")
        preferred_industries = job_market.get("preferred_industries", "")

        if not freq and not companies:
            return None

        score = 0.0
        if freq == "많음":
            score += 30
        elif freq == "보통":
            score += 15

        if companies:
            score += 10

        if req_type:
            score += 5

        if context.goal in ("취업", "이직"):
            score *= 2.0

        if context.goal in ("취업", "이직"):
            if companies:
                company_list = companies.split(",")[0].strip()
                sentence = (
                    f"{company_list} 등 주요 기업에서 채용 시 "
                    f"{req_type} 조건으로 활용되어 취업 경쟁력을 높일 수 있습니다."
                )
            elif preferred_industries:
                sentence = (
                    f"{preferred_industries} 분야에서 채용 공고가 {freq} 편이라 "
                    f"취업에 유리합니다."
                )
            else:
                sentence = f"채용 공고가 {freq} 편이라 취업 경쟁력을 높일 수 있습니다."
        else:
            if companies:
                sentence = (
                    f"{companies} 등에서 선호하는 자격증으로 "
                    f"경력 개발에 도움이 됩니다."
                )
            else:
                sentence = (
                    f"채용 시장에서 수요가 {freq} 편으로 "
                    f"커리어 성장에 도움이 됩니다."
                )

        return StrengthResult(name="job_market", score=score, sentence=sentence)

    def _salary_strength(
        self, cert: dict, context: StructuredUserContext
    ) -> StrengthResult | None:
        """연봉 프리미엄 강점 분석."""
        job_market = cert.get("job_market_info", {})
        salary_premium = job_market.get("salary_premium", "")

        if not salary_premium:
            return None

        score = 20.0

        if context.goal == "전문성 강화":
            score *= 2.0

        if context.goal == "전문성 강화":
            sentence = (
                f"취득 시 연봉 프리미엄({salary_premium})이 기대되어 "
                f"전문 역량 강화와 함께 경력 가치를 높일 수 있습니다."
            )
        elif context.goal in ("취업", "이직"):
            sentence = (
                f"연봉 프리미엄({salary_premium})이 보고되어 "
                f"취업 후 경쟁력 있는 보상을 기대할 수 있습니다."
            )
        else:
            sentence = f"취득 시 연봉 {salary_premium} 효과가 보고되고 있습니다."

        return StrengthResult(name="salary", score=score, sentence=sentence)

    def _non_major_strength(
        self, cert: dict, context: StructuredUserContext
    ) -> StrengthResult | None:
        """비전공자 접근성 강점 분석."""
        feasibility = cert.get("feasibility_info", {})
        self_study = feasibility.get("self_study_possible", False)
        non_major_rate = feasibility.get("non_major_pass_rate", "")

        if not self_study and not non_major_rate:
            return None

        if context.major_background != "비전공자":
            return None

        score = 30.0

        parts = []
        if self_study:
            parts.append("독학으로 준비 가능하고")
        if non_major_rate:
            parts.append(f"비전공자 합격률이 {non_major_rate}로")

        if parts:
            detail = ", ".join(parts)
            sentence = f"{detail} 비전공자도 충분히 도전할 수 있습니다."
        else:
            sentence = "비전공자도 접근 가능한 자격증입니다."

        return StrengthResult(name="non_major", score=score, sentence=sentence)

    def _worker_friendly_strength(
        self, cert: dict, context: StructuredUserContext
    ) -> StrengthResult | None:
        """재직자 친화 강점 분석."""
        study_days = cert.get("study_period_days")
        max_days = context.max_study_period_days

        if study_days is None or max_days is None:
            return None

        if context.employment_status != "재직 중":
            return None

        if study_days > max_days * 0.7:
            return None

        score = 25.0

        months = max(1, study_days // 30)
        sentence = (
            f"약 {months}개월이면 준비 가능하여 "
            f"재직 중에도 무리 없이 취득할 수 있습니다."
        )

        return StrengthResult(name="worker_friendly", score=score, sentence=sentence)

    def _cost_efficiency_strength(
        self, cert: dict, context: StructuredUserContext
    ) -> StrengthResult | None:
        """비용 효율 강점 분석."""
        cost_info = cert.get("cost_info", {})
        exam_fee = cost_info.get("exam_fee", "")

        if not exam_fee:
            return None

        score = 10.0

        sentence = f"응시료가 {exam_fee}으로 부담 없이 도전할 수 있습니다."

        return StrengthResult(name="cost_efficiency", score=score, sentence=sentence)

    def _public_sector_strength(
        self, cert: dict, context: StructuredUserContext
    ) -> StrengthResult | None:
        """공공 부문 가산점 강점 분석."""
        public_info = cert.get("public_sector_info", {})
        points = public_info.get("points", "")

        if not points:
            return None

        score = 15.0

        if context.goal == "취업":
            score *= 1.5

        sentence = (
            f"공공기관 채용 시 {points} 가산점이 부여되어 "
            f"취업 기회를 넓힐 수 있습니다."
        )

        return StrengthResult(name="public_sector", score=score, sentence=sentence)

    def _feasibility_strength(
        self, cert: dict, context: StructuredUserContext
    ) -> StrengthResult | None:
        """실현 가능성 강점 분석."""
        career_info = cert.get("career_info", {})
        industry = career_info.get("industry", "")
        study_days = cert.get("study_period_days")

        if not industry and study_days is None:
            return None

        score = 15.0

        if industry and context.preferred_industries:
            for pref in context.preferred_industries:
                if pref in industry:
                    score += 10
                    break

        if industry and study_days:
            months = max(1, study_days // 30)
            sentence = (
                f"{industry} 분야에서 활용도가 높으며, "
                f"약 {months}개월의 준비 기간이 소요됩니다."
            )
        elif industry:
            sentence = f"{industry} 분야에서 활용도가 높은 자격증입니다."
        else:
            months = max(1, study_days // 30)
            sentence = f"약 {months}개월의 준비 기간으로 취득이 가능합니다."

        return StrengthResult(name="feasibility", score=score, sentence=sentence)

    def _fallback_reason(self, cert: dict, context: StructuredUserContext) -> str:
        """최소한의 데이터로 기본 추천 이유를 생성한다."""
        title = cert.get("title", "이 자격증")
        study_days = cert.get("study_period_days")
        difficulty = cert.get("difficulty")

        parts = [f"{title}은(는)"]

        if study_days:
            months = max(1, study_days // 30)
            parts.append(f"약 {months}개월 준비로 취득 가능하며")

        if difficulty is not None:
            diff_map = {
                1: "낮은",
                2: "비교적 낮은",
                3: "보통",
                4: "높은",
                5: "매우 높은",
            }
            diff_text = diff_map.get(difficulty, "보통")
            parts.append(f"{diff_text} 난이도의 자격증입니다.")
        else:
            parts.append("도전해볼 만한 자격증입니다.")

        goal_suffix = {
            "취업": " 취업 준비에 도움이 될 수 있습니다.",
            "이직": " 이직 준비에 도움이 될 수 있습니다.",
            "전문성 강화": " 전문성 강화에 기여할 수 있습니다.",
            "개인 관심": " 개인 역량 개발에 도움이 됩니다.",
            "창업": " 실무 역량 향상에 기여합니다.",
        }
        suffix = goal_suffix.get(context.goal, "")
        if suffix:
            parts.append(suffix)

        return " ".join(parts)
