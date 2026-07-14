# TeumSeoul Backend

FastAPI·SQLAlchemy·SQLite 기반 TeumSeoul 백엔드입니다. Python 3.11 이상을 권장합니다. API 계약은 `.docs`의 v2.2 문서를 따르며 Base URL은 `/api`입니다.

## 로컬 실행

PowerShell에서 `backend` 디렉터리로 이동한 후 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

- API 문서: http://localhost:8000/docs
- 상태 확인: http://localhost:8000/api/health

## 검사

```powershell
pytest
ruff check .
```

## 구조

```text
backend/
├── app/
│   ├── api/                # 공통 라우터 조립
│   ├── core/               # 설정·예외·로깅
│   ├── db/                 # SQLAlchemy Base·세션
│   ├── models/             # ORM 모델
│   ├── repositories/       # DB 쿼리(도메인 구현 시 추가)
│   ├── routers/            # BE1·BE2 독립 라우터
│   ├── schemas/            # 요청·응답 스키마
│   ├── services/           # 업무 로직(도메인 구현 시 추가)
│   └── main.py             # FastAPI 앱 진입점
└── tests/                  # API 테스트
```

## 협업 경계

- BE1: 데이터·장소·지도·추천·메타, `app/routers/be1.py`에서 라우터 연결
- BE2: 게시글·챗봇, `app/routers/be2.py`에서 라우터 연결
- 공통: `core`, `db`, `schemas/common.py`, `routers/system.py`

확정 ERD, 파일 소유권, 구현 순서와 PR 규칙은 [`.docs/BE_COLLABORATION.md`](.docs/BE_COLLABORATION.md)를 확인합니다.

## 주요 환경변수

`.env.example`을 `.env`로 복사하고 실제 값만 변경합니다. 운영 환경에서는 `ALLOWED_ORIGINS`에 실제 Netlify 도메인을 설정해야 합니다. `OPENAI_API_KEY`와 `.db` 파일은 Git에 포함되지 않습니다.

## Render

저장소 루트의 `render.yaml`은 백엔드 root directory, `/api/health`, SQLite persistent disk를 설정합니다. persistent disk가 필요한 구성이라 유료 Starter 플랜을 기준으로 하며, `ALLOWED_ORIGINS`와 `OPENAI_API_KEY`는 Render에서 직접 입력합니다.

앱 시작 시 `locations`가 정확히 6,518건인지 확인하고, 비어 있거나 불완전하면 `data/locations`의 원본 JSON 7종을 `/var/data/localhub.db`에 자동 적재합니다. 로컬에서 직접 실행하려면 다음 명령을 사용합니다.

```powershell
python -m scripts.seed_locations
```

## 데이터 출처

이 서비스는 한국관광공사 Tour API(TourAPI 4.0)의 데이터를 활용하였습니다.

- 출처: 한국관광공사
- 원본 API: https://www.data.go.kr/data/15101578/openapi.do
- 라이선스: 공공누리 제3유형(출처 표시·변경 금지)

원본 JSON은 수정하지 않으며, 서비스용 정규화 값과 함께 각 원본 객체를 `raw_json`에 보존합니다. 원천 좌표가 서울 범위를 벗어난 항목은 원본을 유지하되 지도·주변 추천용 좌표를 `NULL`로 저장합니다.
