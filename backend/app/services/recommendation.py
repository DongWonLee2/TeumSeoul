import json
import logging
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from itertools import combinations, permutations
from typing import TypeVar

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
ValueT = TypeVar("ValueT")

CANDIDATE_QUERY_LIMIT = 500
COURSE_COUNT = 3
COURSE_OPTION_LIMIT = 24
EARTH_RADIUS_KM = 6371.0088
WALKING_SPEED_KMH = 4.0
ROUTE_DISTANCE_FACTOR = 1.25
TRANSFER_BUFFER_MINUTES = 5

FALLBACK_WARNING = "AI 코스 선택에 실패하거나 비활성화되어 검증된 상위 코스를 제공합니다."
ROUTE_WARNING = "이동시간과 거리는 직선거리 기반의 보수적인 예상값이며 최적 경로가 아닙니다."
VISIT_TIME_WARNING = "장소별 체류시간은 콘텐츠 유형을 바탕으로 한 예상값입니다."

MOOD_CONTENT_TYPES = {
    "healing": (12, 14, 28),
    "culture": (14, 12, 15),
    "activity": (28, 12),
    "night_view": (12, 25),
    "shopping": (38, 12),
}
TYPE_LIMITS = {
    "healing": {12: 8, 14: 6, 28: 4},
    "culture": {14: 6, 12: 10, 15: 2},
    "activity": {28: 9, 12: 9},
    "night_view": {12: 12, 25: 6},
    "shopping": {38: 10, 12: 8},
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
    "culture": ("문화", "미술", "박물", "전시", "공연", "전통", "역사"),
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

EXPERIENCE_NAMES = {
    "museum_art": "박물관·미술관",
    "history_tradition": "역사·전통문화",
    "experience": "체험·공방",
    "performance_event": "공연·축제",
    "walk_outdoor": "산책·야외",
    "market_shopping": "시장·쇼핑",
    "sports_activity": "레포츠·활동",
    "general_culture": "일반 문화시설",
    "general_attraction": "일반 관광지",
    "travel_course": "여행코스",
}
EXPERIENCE_VISIT_MINUTES = {
    "museum_art": 60,
    "history_tradition": 45,
    "experience": 60,
    "performance_event": 90,
    "walk_outdoor": 25,
    "market_shopping": 45,
    "sports_activity": 60,
    "general_culture": 45,
    "general_attraction": 30,
    "travel_course": 25,
}
MOOD_EXPERIENCE_TYPES = {
    "healing": {
        "museum_art",
        "history_tradition",
        "experience",
        "walk_outdoor",
        "sports_activity",
        "general_culture",
        "general_attraction",
    },
    "culture": {
        "museum_art",
        "history_tradition",
        "experience",
        "performance_event",
        "walk_outdoor",
        "general_culture",
        "general_attraction",
    },
    "activity": {
        "history_tradition",
        "experience",
        "walk_outdoor",
        "sports_activity",
        "general_attraction",
    },
    "night_view": {
        "history_tradition",
        "walk_outdoor",
        "general_attraction",
        "travel_course",
    },
    "shopping": {
        "history_tradition",
        "experience",
        "walk_outdoor",
        "market_shopping",
        "general_attraction",
    },
}

MUSEUM_KEYWORDS = ("박물관", "미술관", "갤러리", "아카이브")
HISTORY_KEYWORDS = (
    "궁",
    "종묘",
    "사찰",
    "성곽",
    "유적",
    "역사",
    "전통",
    "한옥",
    "문화재",
)
EXPERIENCE_KEYWORDS = ("체험", "공방", "클래스", "교육관", "만들기")
OUTDOOR_KEYWORDS = ("공원", "산책", "거리", "광장", "한강", "전망", "숲", "둘레길")


@dataclass(frozen=True)
class ScoredCandidate:
    location: Location
    score: float
    experience_type: str
    visit_minutes: int


@dataclass(frozen=True)
class CourseOption:
    id: str
    candidates: tuple[ScoredCandidate, ...]
    estimated_duration_minutes: int
    estimated_travel_minutes: int
    estimated_distance_km: float
    score: float

    @property
    def location_ids(self) -> tuple[int, ...]:
        return tuple(candidate.location.id for candidate in self.candidates)

    @property
    def experience_types(self) -> tuple[str, ...]:
        return tuple(candidate.experience_type for candidate in self.candidates)


def recommend_situational(
    db: Session,
    request: SituationalRecommendationRequest,
) -> SituationalRecommendationResponse:
    candidates, warnings = _build_candidate_pool(db, request)
    applied_conditions = AppliedConditions(**request.model_dump())
    if not candidates:
        return _empty_response(applied_conditions, warnings)

    course_options = _build_course_options(candidates, request, require_diversity=True)
    if len(course_options) < COURSE_COUNT:
        course_options = _build_course_options(candidates, request, require_diversity=False)
        warnings.append("엄격한 유형 다양성 조건으로 코스가 부족해 일부 조건을 완화했습니다.")
    if not course_options:
        return _empty_response(applied_conditions, warnings)

    ai_selection = _request_openai_recommendations(course_options, request)
    recommendations = _courses_from_ai(ai_selection, course_options, request)
    fallback = recommendations is None
    if fallback:
        selected_options = _select_fallback_options(course_options)
        recommendations = [
            _to_course(index, option, request, ai_course=None)
            for index, option in enumerate(selected_options, start=1)
        ]
        warnings.append(FALLBACK_WARNING)
    if len(recommendations) < COURSE_COUNT:
        warnings.append("시간·거리 조건을 만족하는 후보가 부족해 3개 미만의 코스를 반환합니다.")

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


def _empty_response(
    applied_conditions: AppliedConditions,
    warnings: list[str],
) -> SituationalRecommendationResponse:
    return SituationalRecommendationResponse(
        data=SituationalRecommendationData(
            recommendations=[],
            applied_conditions=applied_conditions,
        ),
        meta=SituationalRecommendationMeta(
            count=0,
            fallback=True,
            warnings=[*warnings, "조건과 시간 예산을 만족하는 장소 후보가 없습니다."],
            model=settings.openai_model,
        ),
    )


def _build_candidate_pool(
    db: Session,
    request: SituationalRecommendationRequest,
) -> tuple[list[ScoredCandidate], list[str]]:
    content_type_ids = set(MOOD_CONTENT_TYPES[request.mood])
    latitude = request.current_location.latitude if request.current_location else None
    longitude = request.current_location.longitude if request.current_location else None
    locations = find_recommendation_candidates(
        db,
        content_type_ids=content_type_ids,
        district=request.district,
        latitude=latitude,
        longitude=longitude,
        limit=CANDIDATE_QUERY_LIMIT,
    )
    warnings: list[str] = []

    scored: list[ScoredCandidate] = []
    for location in locations:
        experience_type = _classify_experience(location)
        if experience_type not in MOOD_EXPERIENCE_TYPES[request.mood]:
            continue
        scored.append(
            ScoredCandidate(
                location=location,
                score=_score_location(location, request),
                experience_type=experience_type,
                visit_minutes=EXPERIENCE_VISIT_MINUTES[experience_type],
            )
        )
    scored.sort(key=lambda candidate: (-candidate.score, candidate.location.id))
    return _select_balanced_candidates(scored, request.mood), warnings


def _score_location(location: Location, request: SituationalRecommendationRequest) -> float:
    preferred_types = MOOD_CONTENT_TYPES[request.mood]
    type_rank = preferred_types.index(location.content_type_id)
    score = 35.0 - type_rank * 3
    haystack = f"{location.title} {location.address or ''}".lower()
    score += sum(4 for keyword in MOOD_KEYWORDS[request.mood] if keyword in haystack)
    score += sum(2 for keyword in COMPANION_KEYWORDS[request.companion] if keyword in haystack)
    if request.district and location.district == request.district:
        score += 10
    if location.image_url:
        score += 2
    score += max(0, location.source_modified_at.year - 2020) * 0.2
    if request.current_location:
        distance = _distance_km(
            request.current_location.latitude,
            request.current_location.longitude,
            location.latitude,
            location.longitude,
        )
        score -= min(distance, 20) * 3
    return score


def _classify_experience(location: Location) -> str:
    title = location.title.lower()
    if any(keyword in title for keyword in MUSEUM_KEYWORDS):
        return "museum_art"
    if location.content_type_id == 15 or "공연" in title or "축제" in title:
        return "performance_event"
    if any(keyword in title for keyword in EXPERIENCE_KEYWORDS):
        return "experience"
    if any(keyword in title for keyword in HISTORY_KEYWORDS):
        return "history_tradition"
    if any(keyword in title for keyword in OUTDOOR_KEYWORDS):
        return "walk_outdoor"
    if location.content_type_id == 38 or "시장" in title or "상가" in title:
        return "market_shopping"
    if location.content_type_id == 28:
        return "sports_activity"
    if location.content_type_id == 25:
        return "travel_course"
    if location.content_type_id == 14:
        return "general_culture"
    return "general_attraction"


def _select_balanced_candidates(
    scored: list[ScoredCandidate],
    mood: str,
) -> list[ScoredCandidate]:
    buckets: dict[int, list[ScoredCandidate]] = defaultdict(list)
    for candidate in scored:
        buckets[candidate.location.content_type_id].append(candidate)

    selected: list[ScoredCandidate] = []
    counts: Counter[int] = Counter()
    type_order = MOOD_CONTENT_TYPES[mood]
    while len(selected) < settings.recommendation_candidate_limit:
        added = False
        for content_type_id in type_order:
            limit = TYPE_LIMITS[mood][content_type_id]
            if counts[content_type_id] >= limit or not buckets[content_type_id]:
                continue
            selected.append(buckets[content_type_id].pop(0))
            counts[content_type_id] += 1
            added = True
            if len(selected) >= settings.recommendation_candidate_limit:
                break
        if not added:
            break
    return selected


def _build_course_options(
    candidates: list[ScoredCandidate],
    request: SituationalRecommendationRequest,
    *,
    require_diversity: bool,
) -> list[CourseOption]:
    options: list[CourseOption] = []
    max_places = min(4, len(candidates))
    for place_count in range(1, max_places + 1):
        for group in combinations(candidates, place_count):
            if not _is_valid_experience_mix(group, request, require_diversity):
                continue
            ordered = _order_course(group, request)
            travel_minutes, distance_km = _estimate_travel(ordered, request)
            duration = sum(candidate.visit_minutes for candidate in ordered) + travel_minutes
            if duration > request.available_minutes:
                continue
            utilization = duration / request.available_minutes
            diversity = len(set(candidate.experience_type for candidate in ordered))
            score = (
                sum(candidate.score for candidate in ordered)
                + diversity * 12
                + utilization * 15
                - distance_km * 4
            )
            options.append(
                CourseOption(
                    id="",
                    candidates=ordered,
                    estimated_duration_minutes=duration,
                    estimated_travel_minutes=travel_minutes,
                    estimated_distance_km=round(distance_km, 2),
                    score=score,
                )
            )

    options.sort(
        key=lambda option: (
            -option.score,
            -len(option.candidates),
            option.location_ids,
        )
    )
    diversified = _diversify_course_options(options)
    return [
        replace(option, id=f"candidate-{index}")
        for index, option in enumerate(diversified, start=1)
    ]


def _is_valid_experience_mix(
    group: tuple[ScoredCandidate, ...],
    request: SituationalRecommendationRequest,
    require_diversity: bool,
) -> bool:
    if len({candidate.location.title.strip().lower() for candidate in group}) != len(group):
        return False
    counts = Counter(candidate.experience_type for candidate in group)
    museum_limit = 2 if request.available_minutes == 240 else 1
    if counts["museum_art"] > museum_limit or counts["performance_event"] > 1:
        return False
    if require_diversity and len(group) >= 2 and len(counts) < 2:
        return False
    if require_diversity and request.mood == "culture" and max(counts.values()) > 1:
        return False
    if (
        require_diversity
        and request.mood not in {"culture", "shopping"}
        and max(counts.values()) > 2
    ):
        return False
    if require_diversity and request.mood == "shopping" and counts["market_shopping"] > 3:
        return False
    return True


def _order_course(
    group: tuple[ScoredCandidate, ...],
    request: SituationalRecommendationRequest,
) -> tuple[ScoredCandidate, ...]:
    if len(group) == 1:
        return group
    possible_orders = permutations(group)
    return min(
        possible_orders,
        key=lambda order: _route_distance(order, request),
    )


def _route_distance(
    ordered: tuple[ScoredCandidate, ...],
    request: SituationalRecommendationRequest,
) -> float:
    distance = 0.0
    if request.current_location:
        first = ordered[0].location
        distance += _distance_km(
            request.current_location.latitude,
            request.current_location.longitude,
            first.latitude,
            first.longitude,
        )
    for first, second in zip(ordered, ordered[1:], strict=False):
        distance += _location_distance(first.location, second.location)
    return distance


def _estimate_travel(
    ordered: tuple[ScoredCandidate, ...],
    request: SituationalRecommendationRequest,
) -> tuple[int, float]:
    distance_km = _route_distance(ordered, request)
    walking_minutes = math.ceil(
        distance_km * ROUTE_DISTANCE_FACTOR / WALKING_SPEED_KMH * 60
    )
    transfer_minutes = max(0, len(ordered) - 1) * TRANSFER_BUFFER_MINUTES
    return walking_minutes + transfer_minutes, distance_km


def _diversify_course_options(options: list[CourseOption]) -> list[CourseOption]:
    selected: list[CourseOption] = []
    used_location_ids: set[int] = set()
    for _ in range(COURSE_COUNT):
        option = next(
            (
                candidate
                for candidate in options
                if candidate not in selected
                and not used_location_ids.intersection(candidate.location_ids)
            ),
            None,
        )
        if option is None:
            break
        selected.append(option)
        used_location_ids.update(option.location_ids)

    experience_signature_counts: Counter[tuple[str, ...]] = Counter()
    for option in selected:
        signature = tuple(sorted(set(option.experience_types)))
        experience_signature_counts[signature] += 1
    for option in options:
        if option in selected:
            continue
        signature = tuple(sorted(set(option.experience_types)))
        if experience_signature_counts[signature] >= 8:
            continue
        selected.append(option)
        experience_signature_counts[signature] += 1
        if len(selected) >= COURSE_OPTION_LIMIT:
            break
    return selected


def _request_openai_recommendations(
    course_options: list[CourseOption],
    request: SituationalRecommendationRequest,
) -> AICourseSelection | None:
    if len(course_options) < COURSE_COUNT:
        return None
    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
    if not api_key.strip():
        return None
    option_payload = [
        {
            "candidate_course_id": option.id,
            "estimated_duration_minutes": option.estimated_duration_minutes,
            "estimated_travel_minutes": option.estimated_travel_minutes,
            "estimated_distance_km": option.estimated_distance_km,
            "locations": [
                {
                    "id": candidate.location.id,
                    "title": candidate.location.title,
                    "content_type": CONTENT_TYPES[candidate.location.content_type_id]["name"],
                    "experience_type": EXPERIENCE_NAMES[candidate.experience_type],
                    "estimated_visit_minutes": candidate.visit_minutes,
                    "district": candidate.location.district,
                }
                for candidate in option.candidates
            ],
        }
        for option in course_options
    ]
    try:
        client = OpenAI(
            api_key=api_key.strip(),
            timeout=settings.recommendation_timeout_seconds,
            max_retries=1,
        )
        response = client.responses.parse(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "당신은 서울 여행 코스 큐레이터입니다. 서버가 시간·거리·유형 조건을 "
                        "검증한 후보 코스 중 정확히 3개를 선택하세요. 세 코스는 장소가 겹치지 "
                        "않고 경험과 테마가 서로 달라야 합니다. 사용자 동행과 분위기에 맞는 "
                        "구체적인 제목과 이유를 한국어로 작성하세요. 제공되지 않은 운영시간, "
                        "가격, 행사 개최 여부와 정확한 이동시간은 추측하지 마세요."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "conditions": request.model_dump(mode="json"),
                            "candidate_courses": option_payload,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            text_format=AICourseSelection,
            reasoning={"effort": "low"},
            max_output_tokens=2500,
        )
        return response.output_parsed
    except ValidationError as exc:
        logger.warning(
            "OpenAI recommendation schema fallback: %s",
            exc.errors(include_input=False, include_url=False),
        )
        return None
    except (OpenAIError, TimeoutError, ValueError, TypeError) as exc:
        logger.warning("OpenAI recommendation fallback: %s", type(exc).__name__)
        return None


def _courses_from_ai(
    selection: AICourseSelection | None,
    course_options: list[CourseOption],
    request: SituationalRecommendationRequest,
) -> list[SituationalCourse] | None:
    if selection is None:
        return None
    by_id = {option.id: option for option in course_options}
    selected_ids = [course.candidate_course_id for course in selection.recommendations]
    if len(selected_ids) != COURSE_COUNT or len(set(selected_ids)) != COURSE_COUNT:
        return None
    if any(candidate_id not in by_id for candidate_id in selected_ids):
        return None
    selected_options = [by_id[candidate_id] for candidate_id in selected_ids]
    all_location_ids = [
        location_id
        for option in selected_options
        for location_id in option.location_ids
    ]
    if len(all_location_ids) != len(set(all_location_ids)):
        return None
    return [
        _to_course(index, option, request, ai_course=ai_course)
        for index, (ai_course, option) in enumerate(
            zip(selection.recommendations, selected_options, strict=True),
            start=1,
        )
    ]


def _select_fallback_options(course_options: list[CourseOption]) -> list[CourseOption]:
    if len(course_options) <= COURSE_COUNT:
        return course_options
    option_groups = combinations(course_options, COURSE_COUNT)
    ranked: list[tuple[int, float, tuple[CourseOption, ...]]] = []
    for group in option_groups:
        all_ids = [location_id for option in group for location_id in option.location_ids]
        duplicate_count = len(all_ids) - len(set(all_ids))
        theme_count = len({tuple(sorted(set(option.experience_types))) for option in group})
        score = sum(option.score for option in group) + theme_count * 10
        ranked.append((duplicate_count, -score, group))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return list(ranked[0][2])


def _to_course(
    index: int,
    option: CourseOption,
    request: SituationalRecommendationRequest,
    *,
    ai_course: AICourse | None,
) -> SituationalCourse:
    locations = [candidate.location for candidate in option.candidates]
    latitudes = [location.latitude for location in locations]
    longitudes = [location.longitude for location in locations]
    warnings = [ROUTE_WARNING, VISIT_TIME_WARNING]
    if any(location.content_type_id == 25 for location in locations):
        warnings.append("여행코스 좌표는 전체 경로가 아닌 대표 위치입니다.")
    if any(location.content_type_id == 15 for location in locations):
        warnings.append("축제·공연의 실제 개최 여부와 시간을 별도로 확인해야 합니다.")

    if ai_course:
        title = ai_course.title
        reason = ai_course.reason
    else:
        experience_names = _deduplicate(
            [EXPERIENCE_NAMES[candidate.experience_type] for candidate in option.candidates]
        )
        title = f"{request.district or '서울'} {'·'.join(experience_names)} 코스 {index}"
        reason = (
            f"{COMPANION_NAMES[request.companion]} {option.estimated_duration_minutes}분 정도 "
            f"즐길 수 있도록 가까운 {MOOD_NAMES[request.mood]} 장소를 구성했습니다."
        )

    return SituationalCourse(
        id=f"situational-{index}",
        title=title,
        reason=reason,
        representative_location=RepresentativeLocation(
            latitude=sum(latitudes) / len(latitudes),
            longitude=sum(longitudes) / len(longitudes),
        ),
        estimated_place_count=len(locations),
        estimated_duration_minutes=option.estimated_duration_minutes,
        estimated_travel_minutes=option.estimated_travel_minutes,
        estimated_distance_km=option.estimated_distance_km,
        locations=[_to_recommended_location(candidate, request) for candidate in option.candidates],
        warnings=warnings,
    )


def _to_recommended_location(
    candidate: ScoredCandidate,
    request: SituationalRecommendationRequest,
) -> RecommendedLocation:
    location = candidate.location
    match_reasons = [
        CONTENT_TYPES[location.content_type_id]["name"],
        EXPERIENCE_NAMES[candidate.experience_type],
        MOOD_NAMES[request.mood],
    ]
    if request.district and location.district == request.district:
        match_reasons.append(request.district)
    match_reasons.append(f"{request.available_minutes}분 조건")
    return RecommendedLocation(
        id=location.id,
        title=location.title,
        content_type=CONTENT_TYPES[location.content_type_id]["name"],
        address=location.address,
        image_url=location.image_url,
        experience_type=EXPERIENCE_NAMES[candidate.experience_type],
        estimated_visit_minutes=candidate.visit_minutes,
        match_reasons=match_reasons,
    )


def _location_distance(first: Location, second: Location) -> float:
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


def _deduplicate(values: list[ValueT]) -> list[ValueT]:
    return list(dict.fromkeys(values))
