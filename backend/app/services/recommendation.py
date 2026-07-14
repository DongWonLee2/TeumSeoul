import json
import logging
import math
from collections import Counter
from dataclasses import dataclass
from itertools import combinations

from openai import OpenAI, OpenAIError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import CONTENT_TYPES
from app.models.location import Location
from app.repositories.location import find_recommendation_candidates
from app.schemas.recommendation import (
    AICourse,
    AICourseSelection,
    AppliedConditions,
    RecommendedLocation,
    RepresentativeLocation,
    SituationalCourse,
    SituationalRecommendationData,
    SituationalRecommendationMeta,
    SituationalRecommendationRequest,
    SituationalRecommendationResponse,
)

logger = logging.getLogger(__name__)

CANDIDATE_QUERY_LIMIT = 500
COURSE_COUNT = 3
EARTH_RADIUS_KM = 6371.0088
FALLBACK_WARNING = "AI 코스 생성에 실패하거나 비활성화되어 규칙 기반 결과를 제공합니다."
ROUTE_WARNING = "정확한 이동시간과 최적 경로는 제공하지 않습니다."

MOOD_CONTENT_TYPES = {
    "healing": (12, 14, 28),
    "culture": (14, 12, 15),
    "activity": (28, 12),
    "night_view": (12, 25),
    "shopping": (38, 12),
}
MOOD_NAMES = {
    "healing": "힐링",
    "culture": "문화",
    "activity": "활동",
    "night_view": "야경",
    "shopping": "쇼핑",
}
COMPANION_NAMES = {
    "solo": "혼자",
    "couple": "연인과",
    "friends": "친구와",
    "family": "가족과",
}
MOOD_KEYWORDS = {
    "healing": ("공원", "숲", "산책", "정원", "한강"),
    "culture": ("문화", "미술", "박물", "전시", "공연"),
    "activity": ("체험", "스포츠", "레포츠", "운동"),
    "night_view": ("야경", "전망", "한강", "타워", "빛"),
    "shopping": ("쇼핑", "시장", "백화점", "몰", "상가"),
}
COMPANION_KEYWORDS = {
    "solo": ("도서", "미술", "박물", "산책"),
    "couple": ("공원", "전망", "한강", "정원"),
    "friends": ("체험", "시장", "공연", "레포츠"),
    "family": ("가족", "어린이", "공원", "체험", "박물"),
}
TARGET_PLACE_COUNTS = {30: 1, 60: 2, 120: 3, 240: 4}


@dataclass(frozen=True)
class ScoredCandidate:
    location: Location
    score: float


def recommend_situational(
    db: Session,
    request: SituationalRecommendationRequest,
) -> SituationalRecommendationResponse:
    candidates, warnings = _build_candidate_pool(db, request)
    applied_conditions = AppliedConditions(**request.model_dump(exclude={"current_location"}))
    if not candidates:
        return SituationalRecommendationResponse(
            data=SituationalRecommendationData(
                recommendations=[],
                applied_conditions=applied_conditions,
            ),
            meta=SituationalRecommendationMeta(
                count=0,
                fallback=True,
                warnings=[*warnings, "조건과 일치하는 장소 후보가 없습니다."],
                model=settings.openai_model,
            ),
        )

    ai_selection = _request_openai_recommendations(candidates, request)
    recommendations = _courses_from_ai(ai_selection, candidates, request)
    fallback = recommendations is None
    if fallback:
        recommendations = _build_rule_based_courses(candidates, request)
        warnings.append(FALLBACK_WARNING)
    if len(recommendations) < COURSE_COUNT:
        warnings.append("후보가 부족해 3개 미만의 코스를 반환합니다.")

    return SituationalRecommendationResponse(
        data=SituationalRecommendationData(
            recommendations=recommendations,
            applied_conditions=applied_conditions,
        ),
        meta=SituationalRecommendationMeta(
            count=len(recommendations),
            fallback=fallback,
            warnings=_deduplicate(warnings),
            model=settings.openai_model,
        ),
    )


def _build_candidate_pool(
    db: Session,
    request: SituationalRecommendationRequest,
) -> tuple[list[Location], list[str]]:
    content_type_ids = set(MOOD_CONTENT_TYPES[request.mood])
    locations = find_recommendation_candidates(
        db,
        content_type_ids=content_type_ids,
        district=request.district,
        limit=CANDIDATE_QUERY_LIMIT,
    )
    warnings: list[str] = []
    if len(locations) < COURSE_COUNT and request.district:
        locations = find_recommendation_candidates(
            db,
            content_type_ids=content_type_ids,
            district=None,
            limit=CANDIDATE_QUERY_LIMIT,
        )
        warnings.append("희망 지역의 후보가 부족해 서울 전체로 조건을 완화했습니다.")

    scored = [
        ScoredCandidate(location, _score_location(location, request)) for location in locations
    ]
    scored.sort(key=lambda candidate: (-candidate.score, candidate.location.id))
    return _apply_type_quota(scored, request.mood), warnings


def _score_location(location: Location, request: SituationalRecommendationRequest) -> float:
    preferred_types = MOOD_CONTENT_TYPES[request.mood]
    type_rank = preferred_types.index(location.content_type_id)
    score = 40.0 - type_rank * 8
    haystack = f"{location.title} {location.address or ''}".lower()
    score += sum(5 for keyword in MOOD_KEYWORDS[request.mood] if keyword in haystack)
    score += sum(3 for keyword in COMPANION_KEYWORDS[request.companion] if keyword in haystack)
    if request.district and location.district == request.district:
        score += 12
    if location.image_url:
        score += 2
    score += max(0, location.source_modified_at.year - 2020) * 0.25
    if (
        request.current_location
        and location.latitude is not None
        and location.longitude is not None
    ):
        distance = _distance_km(
            request.current_location.latitude,
            request.current_location.longitude,
            location.latitude,
            location.longitude,
        )
        score += max(0, 20 - distance)
    return score


def _apply_type_quota(scored: list[ScoredCandidate], mood: str) -> list[Location]:
    counts: Counter[int] = Counter()
    selected: list[Location] = []
    for candidate in scored:
        content_type_id = candidate.location.content_type_id
        quota = 15 if mood == "shopping" and content_type_id == 38 else 10
        if mood != "shopping" and content_type_id == 38:
            quota = 5
        if counts[content_type_id] >= quota:
            continue
        selected.append(candidate.location)
        counts[content_type_id] += 1
        if len(selected) >= settings.openai_max_candidates:
            break
    return selected


def _request_openai_recommendations(
    candidates: list[Location],
    request: SituationalRecommendationRequest,
) -> AICourseSelection | None:
    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
    if not api_key.strip():
        return None
    candidate_payload = [
        {
            "id": location.id,
            "title": location.title,
            "content_type": CONTENT_TYPES[location.content_type_id]["name"],
            "district": location.district,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "source_modified_at": location.source_modified_at.isoformat(),
        }
        for location in candidates
    ]
    try:
        client = OpenAI(
            api_key=api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=1,
        )
        response = client.responses.parse(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "당신은 서울 여행 코스 편집자입니다. 제공된 후보 ID만 사용해 서로 다른 "
                        "코스 3개를 만드세요. 운영시간, 가격, 정확한 이동시간과 최적 경로를 "
                        "추측하지 마세요."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "conditions": request.model_dump(mode="json"),
                            "required_place_count": TARGET_PLACE_COUNTS[request.available_minutes],
                            "candidates": candidate_payload,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            text_format=AICourseSelection,
            max_output_tokens=1500,
        )
        return response.output_parsed
    except (OpenAIError, ValidationError, TimeoutError, ValueError, TypeError) as exc:
        logger.warning("OpenAI recommendation fallback: %s", type(exc).__name__)
        return None


def _courses_from_ai(
    selection: AICourseSelection | None,
    candidates: list[Location],
    request: SituationalRecommendationRequest,
) -> list[SituationalCourse] | None:
    if selection is None:
        return None
    by_id = {location.id: location for location in candidates}
    target_count = min(TARGET_PLACE_COUNTS[request.available_minutes], len(candidates))
    signatures: set[frozenset[int]] = set()
    courses: list[SituationalCourse] = []
    for index, ai_course in enumerate(selection.recommendations, start=1):
        if (
            len(ai_course.location_ids) != target_count
            or len(set(ai_course.location_ids)) != target_count
        ):
            return None
        if any(location_id not in by_id for location_id in ai_course.location_ids):
            return None
        signature = frozenset(ai_course.location_ids)
        if signature in signatures:
            return None
        signatures.add(signature)
        locations = [by_id[location_id] for location_id in ai_course.location_ids]
        courses.append(_to_course(index, ai_course, locations, request))
    return courses if len(courses) == COURSE_COUNT else None


def _build_rule_based_courses(
    candidates: list[Location],
    request: SituationalRecommendationRequest,
) -> list[SituationalCourse]:
    target_count = min(TARGET_PLACE_COUNTS[request.available_minutes], len(candidates))
    groups: list[list[Location]] = []
    signatures: set[frozenset[int]] = set()
    for anchor in candidates[:12]:
        nearby = sorted(
            (candidate for candidate in candidates if candidate.id != anchor.id),
            key=lambda candidate: (_location_distance(anchor, candidate), candidate.id),
        )
        group = [anchor, *nearby[: target_count - 1]]
        signature = frozenset(location.id for location in group)
        if len(group) == target_count and signature not in signatures:
            groups.append(group)
            signatures.add(signature)
        if len(groups) == COURSE_COUNT:
            break
    if len(groups) < COURSE_COUNT:
        for group_tuple in combinations(candidates[:12], target_count):
            signature = frozenset(location.id for location in group_tuple)
            if signature not in signatures:
                groups.append(list(group_tuple))
                signatures.add(signature)
            if len(groups) == COURSE_COUNT:
                break

    return [
        _to_course(
            index,
            AICourse(
                title=f"{request.district or '서울'} {MOOD_NAMES[request.mood]} 코스 {index}",
                reason=(
                    f"{COMPANION_NAMES[request.companion]} {request.available_minutes}분 동안 "
                    f"즐기기 좋은 {MOOD_NAMES[request.mood]} 장소를 묶었습니다."
                ),
                location_ids=[location.id for location in group],
            ),
            group,
            request,
        )
        for index, group in enumerate(groups, start=1)
    ]


def _to_course(
    index: int,
    course: AICourse,
    locations: list[Location],
    request: SituationalRecommendationRequest,
) -> SituationalCourse:
    latitudes = [location.latitude for location in locations if location.latitude is not None]
    longitudes = [location.longitude for location in locations if location.longitude is not None]
    warnings = [ROUTE_WARNING]
    if any(location.content_type_id == 25 for location in locations):
        warnings.append("여행코스 좌표는 전체 경로가 아닌 대표 위치입니다.")
    if any(location.content_type_id == 15 for location in locations):
        warnings.append("축제 개최일은 제공 데이터로 확인할 수 없습니다.")
    return SituationalCourse(
        id=f"situational-{index}",
        title=course.title,
        reason=course.reason,
        representative_location=RepresentativeLocation(
            latitude=sum(latitudes) / len(latitudes),
            longitude=sum(longitudes) / len(longitudes),
        ),
        estimated_place_count=len(locations),
        locations=[_to_recommended_location(location, request) for location in locations],
        warnings=warnings,
    )


def _to_recommended_location(
    location: Location,
    request: SituationalRecommendationRequest,
) -> RecommendedLocation:
    match_reasons = [CONTENT_TYPES[location.content_type_id]["name"], MOOD_NAMES[request.mood]]
    if request.district and location.district == request.district:
        match_reasons.append(request.district)
    match_reasons.append(f"{request.available_minutes}분 조건")
    return RecommendedLocation(
        id=location.id,
        title=location.title,
        content_type=CONTENT_TYPES[location.content_type_id]["name"],
        address=location.address,
        image_url=location.image_url,
        match_reasons=match_reasons,
    )


def _location_distance(first: Location, second: Location) -> float:
    if None in (first.latitude, first.longitude, second.latitude, second.longitude):
        return math.inf
    return _distance_km(first.latitude, first.longitude, second.latitude, second.longitude)


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    latitude_delta = math.radians(lat2 - lat1)
    longitude_delta = math.radians(lon2 - lon1)
    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(value))


def _deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
