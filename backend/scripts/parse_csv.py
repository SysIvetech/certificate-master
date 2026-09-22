"""한국 자격증 CSV 데이터를 파싱해 JSON으로 저장하는 스크립트.

종목명(title)을 기준으로 중복을 제거하고, 같은 종목명이 여러 자격구분을 가지면
categories 배열에 모두 포함한다.
"""

import csv
import json
from pathlib import Path
from typing import TypedDict

# 제외할 카테고리 목록
EXCLUDED_CATEGORIES: set[str] = {"일학습병행자격"}
EXCLUDED_CODES: set[str] = {"W"}  # 일학습병행자격 코드


class CategoryInfo(TypedDict):
    """카테고리 정보 타입 정의."""

    code: str
    name: str


class Certificate(TypedDict):
    """파싱된 자격증 데이터 타입 정의."""

    categories: list[CategoryInfo]
    series: str
    title: str
    raw_id: str


class _TitleData(TypedDict):
    """종목명별 임시 데이터 타입."""

    categories: list[CategoryInfo]
    series: str


def parse_csv_to_json(csv_path: Path) -> list[Certificate]:
    """CSV 파일을 파싱해 자격증 목록을 반환한다.

    종목명(title)을 기준으로 그룹화하여 중복을 제거하고,
    같은 종목명이 여러 자격구분을 가지면 categories 배열에 모두 포함한다.
    """
    # 종목명별로 데이터 그룹화
    title_map: dict[str, _TitleData] = {}

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["자격구분코드"].strip()
            category_name = row["자격구분명"].strip()
            title = row["종목명"].strip()
            series = row["계열명"].strip()

            # 제외 카테고리 건너뛰기
            if code in EXCLUDED_CODES or category_name in EXCLUDED_CATEGORIES:
                continue

            category_info: CategoryInfo = {"code": code, "name": category_name}

            if title in title_map:
                # 이미 존재하는 종목명: 카테고리만 추가 (중복 체크)
                existing_categories = title_map[title]["categories"]
                is_duplicate = any(
                    cat["code"] == code and cat["name"] == category_name
                    for cat in existing_categories
                )
                if not is_duplicate:
                    existing_categories.append(category_info)
            else:
                # 새 종목명: 신규 등록
                title_map[title] = {
                    "categories": [category_info],
                    "series": series,
                }

    # Certificate 리스트로 변환
    certificates: list[Certificate] = []
    for title, data in title_map.items():
        # raw_id: 첫 번째 카테고리 코드 사용
        first_code = data["categories"][0]["code"]
        cert: Certificate = {
            "categories": data["categories"],
            "series": data["series"],
            "title": title,
            "raw_id": f"{first_code}_{title}",
        }
        certificates.append(cert)

    return certificates


def save_to_json(certificates: list[Certificate], output_path: Path) -> None:
    """자격증 목록을 JSON 파일로 저장한다."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(certificates, f, ensure_ascii=False, indent=2)


def main() -> None:
    """CSV를 파싱해 JSON으로 저장하는 메인 함수."""
    # Define paths - now data is inside backend/
    data_dir = Path(__file__).parent.parent / "data"
    csv_path = data_dir / "raw" / "credentials.csv"
    output_path = data_dir / "processed" / "certificates_parsed.json"

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse and save
    certificates = parse_csv_to_json(csv_path)
    save_to_json(certificates, output_path)

    # 통계 출력
    single_category = sum(1 for c in certificates if len(c["categories"]) == 1)
    multi_category = sum(1 for c in certificates if len(c["categories"]) > 1)

    print(f"총 {len(certificates)}개의 자격증을 파싱했습니다.")
    print(f"  - 단일 카테고리: {single_category}개")
    print(f"  - 복수 카테고리: {multi_category}개")
    print(f"출력 파일: {output_path}")


if __name__ == "__main__":
    main()
