# 틈서울(TeumSeoul) API 명세서

- API 버전: v1
- Base URL: `/api`
- Content-Type: `application/json`
- 인증: 없음
- 기준 문서: PRD v2.1 상황형 추천 반영
- 상황형 추천 모델: OpenAI API `gpt-5-mini`

---

## 1. 공통 규칙

### 1.1 정상 응답

```json
{
  "data": {},
  "meta": {}
}
```

`meta`가 필요하지 않은 경우 생략할 수 있다.

### 1.2 오류 응답

```json
{
  "detail": "요청한 리소스를 찾을 수 없습니다.",
  "code": "RESOURCE_NOT_FOUND"
}
```

### 1.3 공통 상태 코드

| 코드 | 의미 |
|---:|---|
| 200 | 성공 |
| 201 | 생성 성공 |
| 204 | 삭제 성공 |
| 400 | 잘못된 업무 요청 |
| 403 | 게시글 비밀번호 불일치 |
| 404 | 리소스 없음 |
| 422 | 입력 검증 실패 |
| 429 | 호출 한도 초과 |
| 500 | 서버 오류 |
| 503 | DB 또는 외부 서비스 장애 |

### 1.4 페이지네이션

요청:

```text
?page=1&size=20
```

응답:

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "size": 20,
    "total_items": 6518,
    "total_pages": 326
  }
}
```

- 기본 `page=1`
- 기본 `size=20`
- 최대 `size=100`

---

## 2. 시스템 API

## 2.1 서버 상태

### `GET /api/health`

서버와 DB 연결 상태를 확인한다.

#### 200 Response

```json
{
  "data": {
    "status": "ok",
    "database": "connected",
    "location_count": 6518,
    "timestamp": "2026-07-14T15:00:00+09:00"
  }
}
```

#### 503 Response

```json
{
  "detail": "데이터베이스 연결에 실패했습니다.",
  "code": "DATABASE_UNAVAILABLE"
}
```

---

## 2.2 메타데이터

### `GET /api/meta`

#### 200 Response

```json
{
  "data": {
    "content_types": [
      {"id": 12, "code": "tourist_attraction", "name": "관광지"},
      {"id": 14, "code": "cultural_facility", "name": "문화시설"},
      {"id": 15, "code": "festival_event", "name": "축제공연행사"},
      {"id": 25, "code": "travel_course", "name": "여행코스"},
      {"id": 28, "code": "leports", "name": "레포츠"},
      {"id": 32, "code": "accommodation", "name": "숙박"},
      {"id": 38, "code": "shopping", "name": "쇼핑"}
    ],
    "districts": ["강남구", "강동구", "강북구"],
    "post_categories": ["현장 제보", "방문 후기", "질문", "추천"],
    "status_tags": [
      "혼잡", "여유", "공사", "이용 주의",
      "사진 추천", "가족 추천", "혼자 추천"
    ],
    "recommendation_options": {
      "available_minutes": [30, 60, 120, 240],
      "companions": ["solo", "couple", "friends", "family"],
      "moods": ["healing", "culture", "activity", "night_view", "shopping"]
    }
  }
}
```

---

## 3. 장소 API

## 3.1 장소 목록 조회

### `GET /api/locations`

#### Query Parameters

| 이름 | 타입 | 필수 | 기본값 | 설명 |
|---|---|---:|---|---|
| `q` | string | N |  | 제목·주소 키워드 |
| `content_type_id` | integer | N |  | 12, 14, 15, 25, 28, 32, 38 |
| `district` | string | N |  | 서울 자치구 |
| `has_image` | boolean | N |  | 대표 이미지 유무 |
| `modified_year` | integer | N |  | 원천 데이터 갱신연도 |
| `sort` | string | N | `recent` | `recent`, `title` |
| `page` | integer | N | 1 | 페이지 |
| `size` | integer | N | 20 | 최대 100 |

#### Request Example

```http
GET /api/locations?q=서울숲&content_type_id=12&district=성동구&page=1&size=20
```

#### 200 Response

```json
{
  "data": [
    {
      "id": 101,
      "source_content_id": "128611",
      "content_type_id": 12,
      "content_type": "관광지",
      "title": "서울숲",
      "address": "서울특별시 성동구 뚝섬로 273",
      "district": "성동구",
      "latitude": 37.5430715815,
      "longitude": 127.041798446,
      "image_url": "https://...",
      "source_modified_at": "2026-06-19T09:32:09",
      "warnings": []
    }
  ],
  "meta": {
    "page": 1,
    "size": 20,
    "total_items": 1,
    "total_pages": 1
  }
}
```

#### Errors

- 422 `INVALID_QUERY_PARAMETER`

---

## 3.2 장소 상세 조회

### `GET /api/locations/{location_id}`

#### Path Parameters

| 이름 | 타입 | 설명 |
|---|---|---|
| `location_id` | integer | 내부 장소 ID |

#### 200 Response

```json
{
  "data": {
    "id": 101,
    "source_content_id": "128611",
    "content_type_id": 12,
    "content_type": "관광지",
    "title": "서울숲",
    "address": "서울특별시 성동구 뚝섬로 273",
    "district": "성동구",
    "latitude": 37.5430715815,
    "longitude": 127.041798446,
    "image_url": "https://...",
    "thumbnail_url": "https://...",
    "telephone": null,
    "copyright_code": "Type1",
    "source_modified_at": "2026-06-19T09:32:09",
    "class_codes": ["VE", "VE03", "VE030100"],
    "warnings": ["운영시간은 제공 데이터에 없어 방문 전 확인이 필요합니다."],
    "related_post_count": 2,
    "related_posts": [
      {
        "id": 15,
        "title": "주말 오후에는 사람이 많았어요",
        "category": "현장 제보",
        "status_tag": "혼잡",
        "created_at": "2026-07-15T12:00:00+09:00"
      }
    ],
    "nearby_locations": [
      {
        "id": 102,
        "title": "성수 문화시설",
        "content_type": "문화시설",
        "distance_km": 0.8
      }
    ]
  }
}
```

#### Errors

- 404 `LOCATION_NOT_FOUND`

---

## 3.3 지도 영역 장소 조회

### `GET /api/map/locations`

#### Query Parameters

| 이름 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| `south` | number | Y | 남쪽 위도 |
| `west` | number | Y | 서쪽 경도 |
| `north` | number | Y | 북쪽 위도 |
| `east` | number | Y | 동쪽 경도 |
| `content_type_ids` | string | N | 쉼표 구분 ID |
| `limit` | integer | N | 기본·최대 300 |

#### Request Example

```http
GET /api/map/locations?south=37.50&west=126.95&north=37.58&east=127.08&content_type_ids=12,14&limit=300
```

#### 200 Response

```json
{
  "data": [
    {
      "id": 101,
      "title": "서울숲",
      "content_type_id": 12,
      "content_type": "관광지",
      "district": "성동구",
      "latitude": 37.5430715815,
      "longitude": 127.041798446,
      "thumbnail_url": "https://..."
    }
  ],
  "meta": {
    "count": 1,
    "limit": 300,
    "truncated": false
  }
}
```

#### Errors

- 400 `INVALID_BOUNDS`
- 422 `INVALID_QUERY_PARAMETER`

---

## 4. 상황형 추천 API

## 4.1 상황형 여행코스 추천

### `POST /api/recommend/situational`

SQLite 후보 검색 후 OpenAI API의 `gpt-5-mini`가 후보 장소 안에서 코스 3개와 추천 이유를 생성한다.

#### Request Body

```json
{
  "available_minutes": 120,
  "companion": "friends",
  "mood": "culture",
  "district": "종로구",
  "current_location": {
    "latitude": 37.575,
    "longitude": 126.98
  }
}
```

#### Field Rules

| 필드 | 타입 | 필수 | 허용값 |
|---|---|---:|---|
| `available_minutes` | integer | Y | 30, 60, 120, 240 |
| `companion` | string | Y | `solo`, `couple`, `friends`, `family` |
| `mood` | string | Y | `healing`, `culture`, `activity`, `night_view`, `shopping` |
| `district` | string | N | 서울 자치구 |
| `current_location` | object | N | 위도·경도 |

#### 200 Response

```json
{
  "data": {
    "recommendations": [
      {
        "id": "situational-1",
        "title": "종로 문화 산책",
        "reason": "친구와 2시간 동안 둘러보기 좋은 종로구 문화시설과 인근 관광지를 묶었습니다.",
        "representative_location": {
          "latitude": 37.5794,
          "longitude": 126.9818
        },
        "estimated_place_count": 3,
        "locations": [
          {
            "id": 201,
            "title": "아트선재센터",
            "content_type": "문화시설",
            "address": "서울특별시 종로구 율곡로3길 87",
            "image_url": null,
            "match_reasons": ["종로구", "문화시설", "2시간 조건"]
          }
        ],
        "warnings": [
          "정확한 이동시간과 최적 경로는 제공하지 않습니다."
        ]
      }
    ],
    "applied_conditions": {
      "available_minutes": 120,
      "companion": "friends",
      "mood": "culture",
      "district": "종로구"
    }
  },
  "meta": {
    "count": 3,
    "fallback": false,
    "model": "gpt-5-mini"
  }
}
```

#### 후보 부족 Response

```json
{
  "data": {
    "recommendations": [],
    "applied_conditions": {}
  },
  "meta": {
    "count": 0,
    "fallback": true,
    "warnings": ["조건과 일치하는 후보가 부족하거나 AI 코스 생성에 실패해 폴백 결과를 제공합니다."],
    "model": "gpt-5-mini"
  }
}
```

#### 서버 처리 규칙

1. SQLite에서 조건에 맞는 후보를 조회한다.
2. 쇼핑 편향 방지를 위한 유형별 quota와 거리·갱신일 점수를 적용한다.
3. 후보 장소와 사용자 조건을 `gpt-5-mini`에 전달한다.
4. 모델은 후보 안에서만 장소를 선택해 코스 3개를 JSON으로 반환한다.
5. 서버가 반환된 `location_id`를 후보 목록과 대조해 검증한다.
6. OpenAI 오류·타임아웃·스키마 오류 시 규칙 기반 추천으로 폴백한다.

#### Errors

- 422 `INVALID_RECOMMENDATION_CONDITION`

---

## 5. 게시글 API

## 5.1 게시글 목록

### `GET /api/posts`

#### Query Parameters

| 이름 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| `q` | string | N | 제목·내용·장소명 |
| `category` | string | N | 게시글 카테고리 |
| `status_tag` | string | N | 상태 태그 |
| `location_id` | integer | N | 연결 장소 |
| `district` | string | N | 연결 장소 자치구 |
| `sort` | string | N | `recent`, `views` |
| `page` | integer | N | 기본 1 |
| `size` | integer | N | 기본 20, 최대 100 |

#### 200 Response

```json
{
  "data": [
    {
      "id": 15,
      "location": {
        "id": 101,
        "title": "서울숲"
      },
      "category": "현장 제보",
      "status_tag": "혼잡",
      "title": "주말 오후에는 사람이 많았어요",
      "content_preview": "산책로 입구와 주요 포토존이...",
      "visited_at": "2026-07-13",
      "view_count": 21,
      "created_at": "2026-07-14T10:00:00+09:00",
      "updated_at": "2026-07-14T10:00:00+09:00"
    }
  ],
  "meta": {
    "page": 1,
    "size": 20,
    "total_items": 1,
    "total_pages": 1
  }
}
```

---

## 5.2 게시글 작성

### `POST /api/posts`

#### Request Body

```json
{
  "location_id": 101,
  "category": "현장 제보",
  "status_tag": "혼잡",
  "title": "주말 오후에는 사람이 많았어요",
  "content": "오후 3시쯤 주요 산책로가 혼잡했습니다.",
  "password": "1234",
  "visited_at": "2026-07-13"
}
```

#### Validation

- 제목: 2~100자
- 내용: 2~5,000자
- 비밀번호: 4~30자
- `location_id`: nullable
- `status_tag`: nullable
- `visited_at`: nullable

#### 201 Response

```json
{
  "data": {
    "id": 15,
    "location": {
      "id": 101,
      "title": "서울숲"
    },
    "category": "현장 제보",
    "status_tag": "혼잡",
    "title": "주말 오후에는 사람이 많았어요",
    "content": "오후 3시쯤 주요 산책로가 혼잡했습니다.",
    "visited_at": "2026-07-13",
    "view_count": 0,
    "created_at": "2026-07-14T10:00:00+09:00",
    "updated_at": "2026-07-14T10:00:00+09:00"
  }
}
```

#### Errors

- 404 `LOCATION_NOT_FOUND`
- 422 `INVALID_POST_INPUT`

---

## 5.3 게시글 상세

### `GET /api/posts/{post_id}`

상세 조회 시 조회수를 1 증가시킨다.

#### 200 Response

```json
{
  "data": {
    "id": 15,
    "location": {
      "id": 101,
      "title": "서울숲",
      "address": "서울특별시 성동구 뚝섬로 273",
      "latitude": 37.5430715815,
      "longitude": 127.041798446
    },
    "category": "현장 제보",
    "status_tag": "혼잡",
    "title": "주말 오후에는 사람이 많았어요",
    "content": "오후 3시쯤 주요 산책로가 혼잡했습니다.",
    "visited_at": "2026-07-13",
    "view_count": 22,
    "created_at": "2026-07-14T10:00:00+09:00",
    "updated_at": "2026-07-14T10:00:00+09:00"
  }
}
```

#### Errors

- 404 `POST_NOT_FOUND`

---

## 5.4 게시글 수정

### `PUT /api/posts/{post_id}`

#### Request Body

```json
{
  "password": "1234",
  "location_id": 101,
  "category": "방문 후기",
  "status_tag": "여유",
  "title": "평일 오전에는 여유로웠어요",
  "content": "평일 오전 10시에는 비교적 여유로웠습니다.",
  "visited_at": "2026-07-14"
}
```

#### 200 Response

```json
{
  "data": {
    "id": 15,
    "location": {
      "id": 101,
      "title": "서울숲"
    },
    "category": "방문 후기",
    "status_tag": "여유",
    "title": "평일 오전에는 여유로웠어요",
    "content": "평일 오전 10시에는 비교적 여유로웠습니다.",
    "visited_at": "2026-07-14",
    "view_count": 22,
    "created_at": "2026-07-14T10:00:00+09:00",
    "updated_at": "2026-07-14T11:00:00+09:00"
  }
}
```

#### Errors

- 403 `INVALID_POST_PASSWORD`
- 404 `POST_NOT_FOUND`
- 404 `LOCATION_NOT_FOUND`
- 422 `INVALID_POST_INPUT`

---

## 5.5 게시글 삭제

### `DELETE /api/posts/{post_id}`

#### Request Body

```json
{
  "password": "1234"
}
```

#### 204 Response

응답 본문 없음.

#### Errors

- 403 `INVALID_POST_PASSWORD`
- 404 `POST_NOT_FOUND`

---

## 6. 챗봇 API

## 6.1 검색 기반 챗봇

### `POST /api/chat`

#### Request Body

```json
{
  "message": "종로에서 2시간, 친구와 조용한 문화 분위기로 추천해줘",
  "context": {
    "available_minutes": 120,
    "companion": "friends",
    "mood": "culture",
    "district": "종로구",
    "current_location": null
  },
  "history": [
    {
      "role": "user",
      "content": "서울에서 짧게 둘러볼 곳을 찾고 있어"
    },
    {
      "role": "assistant",
      "content": "원하는 지역과 시간을 알려주세요."
    }
  ]
}
```

#### Validation

| 필드 | 규칙 |
|---|---|
| `message` | 1~1,000자 |
| `context` | 전체 선택 |
| `history` | 브라우저가 전달하는 최근 대화 일부 |
| `history.role` | `user`, `assistant` |
| `history.content` | 길이 제한 적용 |

#### 200 Response

```json
{
  "data": {
    "answer": "종로구에서 친구와 2시간 동안 둘러보기 좋은 문화 후보 3곳입니다.",
    "results": [
      {
        "location_id": 201,
        "title": "아트선재센터",
        "content_type": "문화시설",
        "address": "서울특별시 종로구 율곡로3길 87",
        "reason": "종로구의 문화시설이며 입력한 문화 분위기 조건과 일치합니다.",
        "source_modified_at": "2026-06-11T13:48:41"
      }
    ],
    "community_posts": [
      {
        "post_id": 15,
        "title": "최근 방문 팁",
        "status_tag": "여유",
        "location_id": 201
      }
    ],
    "warnings": [
      "운영시간은 제공 데이터에 없어 방문 전 확인이 필요합니다."
    ],
    "extracted_context": {
      "available_minutes": 120,
      "companion": "friends",
      "mood": "culture",
      "district": "종로구"
    },
    "fallback": false
  }
}
```

#### OpenAI 장애 시 200 Response

```json
{
  "data": {
    "answer": "검색 결과를 바탕으로 후보를 안내합니다.",
    "results": [],
    "community_posts": [],
    "warnings": [
      "AI 요약을 사용할 수 없어 검색 결과 형식으로 제공했습니다."
    ],
    "extracted_context": {},
    "fallback": true
  }
}
```

#### 제한 질의 예시

“오늘 열리는 축제 알려줘”:

```json
{
  "data": {
    "answer": "제공 데이터에는 행사 시작일과 종료일이 없어 오늘 개최 여부를 확인할 수 없습니다. 대신 선택 지역의 축제 후보를 보여드립니다.",
    "results": [],
    "community_posts": [],
    "warnings": [
      "행사 일정은 공식 채널에서 방문 전 확인해 주세요."
    ],
    "extracted_context": {
      "content_type_id": 15
    },
    "fallback": false
  }
}
```

#### Errors

- 422 `INVALID_CHAT_INPUT`
- 429 `AI_RATE_LIMITED`
- 503 `CHAT_SERVICE_UNAVAILABLE`

---

## 7. 데이터 모델 DTO

## 7.1 LocationSummary

```json
{
  "id": 101,
  "source_content_id": "128611",
  "content_type_id": 12,
  "content_type": "관광지",
  "title": "서울숲",
  "address": "서울특별시 성동구 뚝섬로 273",
  "district": "성동구",
  "latitude": 37.5430715815,
  "longitude": 127.041798446,
  "image_url": "https://...",
  "source_modified_at": "2026-06-19T09:32:09",
  "warnings": []
}
```

## 7.2 PostSummary

```json
{
  "id": 15,
  "location": {
    "id": 101,
    "title": "서울숲"
  },
  "category": "현장 제보",
  "status_tag": "혼잡",
  "title": "주말 오후에는 사람이 많았어요",
  "content_preview": "오후 3시쯤...",
  "visited_at": "2026-07-13",
  "view_count": 21,
  "created_at": "2026-07-14T10:00:00+09:00",
  "updated_at": "2026-07-14T10:00:00+09:00"
}
```

## 7.3 Warning

```json
{
  "code": "OPERATING_HOURS_UNAVAILABLE",
  "message": "운영시간은 제공 데이터에 없어 방문 전 확인이 필요합니다."
}
```

MVP에서 프론트엔드 구현 단순화를 위해 `warnings`를 문자열 배열로 먼저 구현하고, 시간이 허용되면 객체 배열로 확장한다.

---

## 8. 오류 코드

| code | HTTP | 의미 |
|---|---:|---|
| `INVALID_QUERY_PARAMETER` | 422 | 검색 파라미터 오류 |
| `INVALID_BOUNDS` | 400 | 지도 영역 좌표 오류 |
| `LOCATION_NOT_FOUND` | 404 | 장소 없음 |
| `POST_NOT_FOUND` | 404 | 게시글 없음 |
| `INVALID_POST_PASSWORD` | 403 | 비밀번호 불일치 |
| `INVALID_POST_INPUT` | 422 | 게시글 검증 실패 |
| `INVALID_RECOMMENDATION_CONDITION` | 422 | 추천 조건 오류 |
| `INVALID_CHAT_INPUT` | 422 | 챗 입력 오류 |
| `AI_RATE_LIMITED` | 429 | `gpt-5-mini` 호출 제한 |
| `DATABASE_UNAVAILABLE` | 503 | DB 연결 실패 |
| `CHAT_SERVICE_UNAVAILABLE` | 503 | 챗봇 처리 실패 |
| `INTERNAL_SERVER_ERROR` | 500 | 알 수 없는 오류 |

---

## 9. 백엔드 담당자별 API 소유권

| API | 주 담당 | 리뷰 |
|---|---|---|
| `GET /api/health` | 공동 | 공동 |
| `GET /api/meta` | BE 1 | BE 2 |
| `GET /api/locations` | BE 1 | BE 2 |
| `GET /api/locations/{id}` | BE 1 | BE 2 |
| `GET /api/map/locations` | BE 1 | BE 2 |
| `POST /api/recommend/situational` | BE 1 | BE 2 |
| `GET /api/posts` | BE 2 | BE 1 |
| `POST /api/posts` | BE 2 | BE 1 |
| `GET /api/posts/{id}` | BE 2 | BE 1 |
| `PUT /api/posts/{id}` | BE 2 | BE 1 |
| `DELETE /api/posts/{id}` | BE 2 | BE 1 |
| `POST /api/chat` | BE 2 | BE 1 |

---

## 10. Swagger 검증 체크리스트

- [ ] health에서 DB 연결과 6,518건 확인
- [ ] meta 옵션 조회
- [ ] locations 복합 필터
- [ ] 장소 상세·관련 글·주변 장소
- [ ] map bounds 정상·오류
- [ ] 상황형 추천 3개 반환
- [ ] 자유 게시글 작성
- [ ] 장소 연결 게시글 작성
- [ ] 게시글 조회수 증가
- [ ] 올바른 비밀번호 수정·삭제
- [ ] 틀린 비밀번호 403
- [ ] 챗봇 장소 추천
- [ ] 챗봇 게시글 검색
- [ ] 오늘 축제 제한 응답
- [ ] OpenAI 장애 폴백
- [ ] 모든 조회 응답에 password 미포함
