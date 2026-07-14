# TeumSeoul 백엔드 병렬 작업 가이드

기준 문서는 기능명세서/API 명세서 v2.2이며, 이 문서는 BE1과 BE2가 같은 파일을 동시에 수정하는 일을 줄이기 위한 실행 계약이다.

## 1. 확정된 공통 계약

- Base URL: `/api`
- 정상 응답: `{"data": ..., "meta": ...}` (`meta`는 불필요하면 생략 가능)
- 오류 응답: `{"detail": "...", "code": "..."}`
- DB: SQLAlchemy 2.x 동기 세션 + SQLite, 요청마다 `get_db()` 사용
- 트랜잭션: Repository는 쿼리만 수행하고 Service가 쓰기 단위의 commit/rollback을 결정
- 시간: DB에는 UTC 기준 naive datetime 저장, API 응답은 ISO 8601로 직렬화
- 페이지: 1부터 시작, 기본 20, 최대 100
- 고정 옵션: `core/constants.py`, 시간 컬럼: `models/mixins.py`를 양쪽 모델에서 재사용
- 삭제: Post는 물리 삭제, Location 삭제 시 연결 Post의 `location_id`는 `SET NULL`
- 보안: 요청 body 전체를 로깅하지 않고 password/API key를 응답 모델에 선언하지 않음


## 2. 파일 소유권과 구현 순서

| 담당 | 단독 소유 파일/영역 | 구현 순서 |
|---|---|---|
| BE1 | `models/location.py`, `schemas/location.py`, `schemas/recommendation.py`, `repositories/location.py`, `services/location.py`, `services/recommendation.py`, `routers/locations.py`, `routers/map.py`, `routers/recommend.py`, `routers/meta.py`, `scripts/seed_locations.py`, `routers/be1.py` | Location 모델 → seed → 조회 Repository → 장소/지도/메타 → 추천/폴백 → 테스트 |
| BE2 | `models/post.py`, `schemas/post.py`, `schemas/chat.py`, `repositories/post.py`, `services/post.py`, `services/chat.py`, `routers/posts.py`, `routers/chat.py`, `routers/be2.py` | Post 모델 → CRUD/비밀번호 → 검색/조회수 → Chat 검색 → OpenAI/폴백 → 테스트 |
| 공동 | `core/**`, `db/**`, `models/mixins.py`, `schemas/common.py`, `routers/system.py`, `main.py`, 의존성, 배포, 이 문서 | 계약 변경은 양쪽 리뷰 후 반영 |

각 담당자는 자신의 도메인 라우터를 마지막에 본인 집계 파일인 `routers/be1.py` 또는 `routers/be2.py`에만 연결한다. `app/api/router.py`와 `app/main.py`는 이미 두 집계 라우터를 로드하므로 수정할 필요가 없다.

## 3. 교차 도메인 규칙

- BE2의 `Post.location_id`는 문자열 참조 `ForeignKey("locations.id", ondelete="SET NULL")`를 사용한다.
- BE2는 장소 존재 여부가 필요할 때 Location Service를 직접 import하지 않고, 공통 Session으로 `locations.id` 존재 쿼리를 수행하는 얇은 Repository 함수를 둔다.
- BE1의 장소 상세 `related_posts`는 Post Service를 import하지 않고 읽기 전용 쿼리/프로토콜로 결합한다. 초기에는 빈 배열과 count 0으로 API를 먼저 완성해도 된다.
- Chat은 BE1 Service 내부 구현에 의존하지 않고 Location/Post Repository의 공개 검색 함수만 조합한다.
- 공유 함수 시그니처 변경은 PR 설명의 `계약 변경`에 표시하고 상대 담당자의 승인을 받는다.

## 4. 완료 체크포인트

### BE1 완료 조건

- 7종 6,518건 seed 및 재실행 중복 0건
- locations 목록·상세, map bounds, meta API 테스트
- 상황형 추천 3개, 후보 검증, OpenAI 실패 폴백 테스트
- Render에서 `/api/health`와 데이터 지속성 확인

### BE2 완료 조건

- posts CRUD·검색·조회수 및 password 미노출 테스트
- 잘못된 비밀번호 403, 없는 장소/글 404
- Chat 근거 ID 검증, 제한 질의, OpenAI 실패 폴백 테스트

### 통합 완료 조건

- 장소 상세의 관련 게시글과 게시글 응답의 장소 요약 확인
- 전체 Swagger 체크리스트 수행
- `location_count=6518`, 제출 DB 중복 0, API key/password 노출 0 확인
- 프런트/Render 실제 도메인만 `ALLOWED_ORIGINS`에 설정
