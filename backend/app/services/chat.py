import json
import re
from collections.abc import Callable
from dataclasses import dataclass, replace

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import CONTENT_TYPES
from app.core.exceptions import AppException
from app.repositories import chat as chat_repository
from app.schemas.chat import (
    AIChatOutput,
    ChatCommunityPost,
    ChatLocationResult,
    ChatRequest,
    ChatResponse,
)

DISTRICT_PATTERN = re.compile(r"([가-힣]{2,5}구)")
SEOUL_DISTRICTS = (
    "강남구",
    "강동구",
    "강북구",
    "강서구",
    "관악구",
    "광진구",
    "구로구",
    "금천구",
    "노원구",
    "도봉구",
    "동대문구",
    "동작구",
    "마포구",
    "서대문구",
    "서초구",
    "성동구",
    "성북구",
    "송파구",
    "양천구",
    "영등포구",
    "용산구",
    "은평구",
    "종로구",
    "중구",
    "중랑구",
)
REFERENCE_PATTERN = re.compile(r"([가-힣A-Za-z0-9·\s]{2,30}?)(?:\s*(?:근처|주변|인근))")
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?i)(password|api[_ -]?key)\s*[:=]\s*\S+"),
)
CONTENT_TYPE_KEYWORDS = {
    12: ("관광", "명소", "공원", "산책"),
    14: ("문화", "미술관", "박물관", "전시"),
    15: ("축제", "공연", "행사"),
    25: ("코스", "동선"),
    28: ("레포츠", "운동", "활동", "액티비티"),
    32: ("숙박", "호텔", "숙소"),
    38: ("쇼핑", "시장", "몰"),
}
MOOD_CONTENT_TYPES = {
    "healing": (12, 14, 28),
    "culture": (14, 12, 15),
    "activity": (28, 12),
    "night_view": (12, 25),
    "shopping": (38, 12),
}
GENERIC_TERMS = {
    "추천",
    "추천해줘",
    "알려줘",
    "서울",
    "장소",
    "곳",
    "어디",
    "친구",
    "가족",
    "혼자",
    "연인",
    "시간",
    "분위기",
    "오늘",
    "현재",
    "지금",
    "영업",
    "중인",
    "열리는",
    "가장",
    "제일",
    "최저가",
    "정확히",
    "최적",
}
STANDARD_WARNING = "운영시간은 제공 데이터에 없어 방문 전 확인이 필요합니다."


@dataclass(frozen=True)
class ExtractedContext:
    available_minutes: int | None = None
    companion: str | None = None
    mood: str | None = None
    district: str | None = None
    content_type_id: int | None = None
    indoor_outdoor: str | None = None
    base_location: str | None = None
    search_posts: bool = False

    def public_dict(self) -> dict[str, object]:
        values = {
            "available_minutes": self.available_minutes,
            "companion": self.companion,
            "mood": self.mood,
            "district": self.district,
            "content_type_id": self.content_type_id,
            "indoor_outdoor": self.indoor_outdoor,
            "base_location": self.base_location,
            "search_posts": self.search_posts or None,
        }
        return {key: value for key, value in values.items() if value is not None}


@dataclass(frozen=True)
class RestrictedQuery:
    answer: str
    warning: str


def handle_chat(
    db: Session,
    payload: ChatRequest,
    ai_generator: Callable[..., AIChatOutput] | None = None,
) -> ChatResponse:
    context = extract_context(payload)
    restriction = detect_restricted_query(payload.message)
    if "축제" in payload.message and ("오늘" in payload.message or "현재" in payload.message):
        context = replace(context, content_type_id=15)

    try:
        reference = (
            chat_repository.find_reference_location(db, context.base_location)
            if context.base_location
            else None
        )
        current_location = payload.context.current_location if payload.context else None
        keywords = extract_search_keywords(payload.message, context)
        content_type_ids = _content_type_ids(context)
        candidates = chat_repository.search_locations(
            db,
            district=context.district,
            content_type_ids=content_type_ids,
            keywords=keywords,
            reference=reference,
            current_latitude=current_location.latitude if current_location else None,
            current_longitude=current_location.longitude if current_location else None,
            limit=settings.openai_max_candidates,
        )
        posts = chat_repository.search_posts(
            db,
            location_ids=tuple(candidate.id for candidate in candidates),
            keywords=keywords if context.search_posts else (),
        )
    except SQLAlchemyError as exc:
        raise AppException(
            503,
            "챗봇 검색 서비스를 사용할 수 없습니다.",
            "CHAT_SERVICE_UNAVAILABLE",
        ) from exc

    if restriction is not None:
        return _restricted_response(restriction, context, candidates, posts)

    generator = ai_generator or generate_ai_output
    try:
        output = generator(payload=payload, context=context, candidates=candidates, posts=posts)
        return _validated_ai_response(output, context, candidates, posts)
    except Exception:
        return _fallback_response(context, candidates, posts)


def extract_context(payload: ChatRequest) -> ExtractedContext:
    message = payload.message
    explicit = payload.context
    district_match = DISTRICT_PATTERN.search(message)
    inferred_district = district_match.group(1) if district_match else next(
        (
            district
            for district in SEOUL_DISTRICTS
            if f"{district[:-1]}에서" in message or f"{district[:-1]} 근처" in message
        ),
        None,
    )
    available_minutes = _extract_minutes(message)
    companion = _match_mapping(
        message,
        {
            "solo": ("혼자",),
            "couple": ("연인", "커플"),
            "friends": ("친구",),
            "family": ("가족", "아이"),
        },
    )
    mood = _match_mapping(
        message,
        {
            "healing": ("힐링", "조용", "산책", "여유"),
            "culture": ("문화", "전시", "박물관", "미술관"),
            "activity": ("활동", "레포츠", "운동", "액티비티"),
            "night_view": ("야경", "밤", "전망"),
            "shopping": ("쇼핑", "시장", "몰"),
        },
    )
    content_type_id = next(
        (
            content_type_id
            for content_type_id, terms in CONTENT_TYPE_KEYWORDS.items()
            if any(term in message for term in terms)
        ),
        None,
    )
    reference_match = REFERENCE_PATTERN.search(message)
    indoor_outdoor = (
        "indoor" if any(term in message for term in ("실내", "비오는", "비 오는")) else None
    )
    if any(term in message for term in ("야외", "밖에서", "공원")):
        indoor_outdoor = "outdoor"
    return ExtractedContext(
        available_minutes=(explicit.available_minutes if explicit else None) or available_minutes,
        companion=(explicit.companion if explicit else None) or companion,
        mood=(explicit.mood if explicit else None) or mood,
        district=(explicit.district.strip() if explicit and explicit.district else None)
        or inferred_district,
        content_type_id=content_type_id,
        indoor_outdoor=indoor_outdoor,
        base_location=reference_match.group(1).strip() if reference_match else None,
        search_posts=any(
            term in message for term in ("제보", "후기", "게시글", "커뮤니티", "혼잡", "공사")
        ),
    )


def detect_restricted_query(message: str) -> RestrictedQuery | None:
    if "축제" in message and any(term in message for term in ("오늘", "현재", "지금")):
        return RestrictedQuery(
            "제공 데이터에는 행사 시작일과 종료일이 없어 오늘 개최 여부를 "
            "확인할 수 없습니다. 대신 검색 조건에 맞는 축제 후보를 보여드립니다.",
            "행사 일정은 공식 채널에서 방문 전 확인해 주세요.",
        )
    if any(term in message for term in ("영업 중", "영업중", "지금 열", "운영 중")):
        return RestrictedQuery(
            "제공 데이터에는 운영시간이 없어 지금 영업 중인지 확인할 수 없습니다. "
            "대신 검색 조건에 맞는 후보를 보여드립니다.",
            STANDARD_WARNING,
        )
    if any(term in message for term in ("가장 싼", "최저가", "제일 싼")) and any(
        term in message for term in ("호텔", "숙박", "숙소")
    ):
        return RestrictedQuery(
            "제공 데이터에는 가격과 예약 가능 여부가 없어 가장 저렴한 숙소를 "
            "판단할 수 없습니다. 대신 숙박 후보를 보여드립니다.",
            "가격·객실·예약 가능 여부는 공식 예약 채널에서 확인해 주세요.",
        )
    if any(term in message for term in ("정확히", "최적 동선", "최적 경로")) and any(
        term in message for term in ("시간", "분", "동선", "경로")
    ):
        return RestrictedQuery(
            "교통 상황과 실제 이동시간 데이터가 없어 정확한 소요시간이나 최적 동선을 "
            "보장할 수 없습니다. 대신 조건에 맞는 장소 후보를 보여드립니다.",
            "정확한 이동시간과 최적 경로는 제공하지 않습니다.",
        )
    return None


def extract_search_keywords(message: str, context: ExtractedContext) -> tuple[str, ...]:
    if context.base_location:
        return ()
    if any(
        (
            context.district,
            context.content_type_id,
            context.mood,
            context.indoor_outdoor,
        )
    ):
        return ()
    tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", message)
    excluded = set(GENERIC_TERMS)
    if context.district:
        excluded.add(context.district)
    for terms in CONTENT_TYPE_KEYWORDS.values():
        excluded.update(terms)
    keywords = [
        token
        for token in tokens
        if token not in excluded
        and not token.endswith(("시간", "에서", "으로", "분위기로", "추천해줘", "알려줘"))
        and not any(
            term in token
            for term in ("조용", "분위기", "추천", "친구", "가족", "혼자", "연인")
        )
    ]
    return tuple(dict.fromkeys(keywords[:3]))


def generate_ai_output(
    *,
    payload: ChatRequest,
    context: ExtractedContext,
    candidates: list[chat_repository.LocationCandidate],
    posts: list[chat_repository.PostCandidate],
) -> AIChatOutput:
    if settings.openai_api_key is None:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.openai_timeout_seconds,
        max_retries=0,
    )
    candidate_payload = [
        {
            "id": item.id,
            "title": item.title,
            "content_type": CONTENT_TYPES[item.content_type_id]["name"],
            "address": item.address,
            "district": item.district,
            "source_modified_at": item.source_modified_at.isoformat()
            if item.source_modified_at
            else None,
        }
        for item in candidates
    ]
    post_payload = [
        {
            "id": item.id,
            "location_id": item.location_id,
            "title": item.title,
            "content": _redact_sensitive(item.content[:300]),
            "status_tag": item.status_tag,
        }
        for item in posts
    ]
    history = [
        {"role": item.role, "content": _redact_sensitive(item.content)}
        for item in payload.history[-10:]
    ]
    prompt_payload = json.dumps(
        {
            "question": _redact_sensitive(payload.message),
            "extracted_context": context.public_dict(),
            "official_location_candidates": candidate_payload,
            "anonymous_community_post_candidates": post_payload,
        },
        ensure_ascii=False,
    )
    response = client.responses.parse(
        model=settings.openai_model,
        input=[
            {
                "role": "system",
                "content": (
                    "당신은 서울 공공데이터 검색 결과만 설명하는 챗봇입니다. 제공된 공식 장소와 "
                    "익명 커뮤니티 후보 밖의 사실, 운영시간, 가격, 행사 일정, 정확한 이동시간을 "
                    "만들지 마세요. 장소는 최대 3개만 선택하고 후보 ID만 사용하세요. 공식 장소와 "
                    "익명 제보를 명확히 구분하세요. 답변과 이유는 한국어로 작성하세요. "
                    "answer는 사용자에게 직접 말하는 자연스러운 한국어 2~4문장으로 작성하고, "
                    "전체 추천을 간결하게 요약하세요. answer에 후보 ID나 게시글 ID, location_id, "
                    "post_id, content_type 같은 내부 필드명, JSON 구조를 노출하지 마세요. 또한 "
                    "'제목:', '주소:', 'ID:' 형식으로 후보 데이터를 그대로 나열하지 마세요. "
                    "장소별 선택과 추천 이유는 recommendations에만 작성하세요."
                ),
            },
            *history,
            {"role": "user", "content": prompt_payload},
        ],
        text_format=AIChatOutput,
        reasoning={"effort": "low"},
        max_output_tokens=3000,
        store=False,
    )
    if response.output_parsed is None:
        raise ValueError("OpenAI response did not match the schema")
    return response.output_parsed


def _validated_ai_response(
    output: AIChatOutput,
    context: ExtractedContext,
    candidates: list[chat_repository.LocationCandidate],
    posts: list[chat_repository.PostCandidate],
) -> ChatResponse:
    candidate_by_id = {candidate.id: candidate for candidate in candidates}
    post_by_id = {post.id: post for post in posts}
    seen_location_ids: set[int] = set()
    results = []
    for recommendation in output.recommendations:
        candidate = candidate_by_id.get(recommendation.location_id)
        if candidate is None or candidate.id in seen_location_ids:
            continue
        seen_location_ids.add(candidate.id)
        results.append(_location_result(candidate, recommendation.reason))
    if candidates and not results:
        raise ValueError("OpenAI returned no valid candidate IDs")
    community_posts = [
        _community_post(post_by_id[post_id])
        for post_id in dict.fromkeys(output.post_ids)
        if post_id in post_by_id
    ][:3]
    return ChatResponse(
        answer=output.answer,
        results=results,
        community_posts=community_posts,
        warnings=list(dict.fromkeys([STANDARD_WARNING, *output.warnings])),
        extracted_context=context.public_dict(),
        fallback=False,
    )


def _fallback_response(
    context: ExtractedContext,
    candidates: list[chat_repository.LocationCandidate],
    posts: list[chat_repository.PostCandidate],
) -> ChatResponse:
    results = [
        _location_result(candidate, _template_reason(candidate, context))
        for candidate in candidates[:3]
    ]
    answer = (
        f"검색 결과를 바탕으로 후보 {len(results)}곳을 안내합니다."
        if results
        else "조건과 일치하는 검색 결과가 없습니다. 지역이나 조건을 완화해 다시 질문해 주세요."
    )
    return ChatResponse(
        answer=answer,
        results=results,
        community_posts=[_community_post(post) for post in posts[:3]],
        warnings=["AI 요약을 사용할 수 없어 검색 결과 형식으로 제공했습니다.", STANDARD_WARNING],
        extracted_context=context.public_dict(),
        fallback=True,
    )


def _restricted_response(
    restriction: RestrictedQuery,
    context: ExtractedContext,
    candidates: list[chat_repository.LocationCandidate],
    posts: list[chat_repository.PostCandidate],
) -> ChatResponse:
    return ChatResponse(
        answer=restriction.answer,
        results=[
            _location_result(candidate, _template_reason(candidate, context))
            for candidate in candidates[:3]
        ],
        community_posts=[_community_post(post) for post in posts[:3]],
        warnings=[restriction.warning],
        extracted_context=context.public_dict(),
        fallback=False,
    )


def _location_result(
    candidate: chat_repository.LocationCandidate, reason: str
) -> ChatLocationResult:
    return ChatLocationResult(
        location_id=candidate.id,
        title=candidate.title,
        content_type=CONTENT_TYPES[candidate.content_type_id]["name"],
        address=candidate.address,
        reason=reason,
        source_modified_at=candidate.source_modified_at.isoformat()
        if candidate.source_modified_at
        else None,
    )


def _community_post(post: chat_repository.PostCandidate) -> ChatCommunityPost:
    return ChatCommunityPost(
        post_id=post.id,
        title=post.title,
        status_tag=post.status_tag,
        location_id=post.location_id,
    )


def _template_reason(
    candidate: chat_repository.LocationCandidate, context: ExtractedContext
) -> str:
    conditions = []
    if context.district and candidate.district == context.district:
        conditions.append(context.district)
    if context.mood:
        conditions.append(f"{context.mood} 분위기")
    conditions.append(CONTENT_TYPES[candidate.content_type_id]["name"])
    return f"입력한 조건과 관련된 {' · '.join(conditions)} 후보입니다."


def _content_type_ids(context: ExtractedContext) -> tuple[int, ...]:
    if context.content_type_id is not None:
        return (context.content_type_id,)
    if context.mood:
        return MOOD_CONTENT_TYPES.get(context.mood, ())
    if context.indoor_outdoor == "indoor":
        return (14, 32, 38)
    if context.indoor_outdoor == "outdoor":
        return (12, 15, 25, 28)
    return ()


def _extract_minutes(message: str) -> int | None:
    if "반나절" in message:
        return 240
    hour_match = re.search(r"(1|2|4)\s*시간", message)
    if hour_match:
        return int(hour_match.group(1)) * 60
    minute_match = re.search(r"(30|60|120|240)\s*분", message)
    return int(minute_match.group(1)) if minute_match else None


def _match_mapping(message: str, mapping: dict[str, tuple[str, ...]]) -> str | None:
    return next(
        (key for key, terms in mapping.items() if any(term in message for term in terms)),
        None,
    )


def _redact_sensitive(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted
