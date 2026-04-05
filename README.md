# Briefwave

Briefwave는 드론과 AI 분야의 글로벌 뉴스, 논문, 리포트를 자동으로 수집하고, 사용자의 관심 키워드에 맞춰 개인화된 인사이트 피드로 재구성하는 뉴스 인텔리전스 플랫폼입니다.

## 핵심 가치

- 자동 수집: 글로벌 뉴스, 연구 자료, 리포트를 하나의 흐름으로 통합
- 개인화 피드: 키워드 구독 기반으로 사용자별 맞춤 뉴스 구성
- AI 보조 분석: 요약, 번역, 카테고리 분류, 트렌드 해석 지원
- 운영 가시성: 소스 상태와 수집 현황, 피드 통계를 함께 관리

## 주요 기능

- 사용자 로그인 및 JWT 기반 인증
- 키워드 구독 생성, 수정, 삭제
- 구독별 수동 크롤링 실행
- 글로벌 뉴스/연구 소스 통합 수집
- 번역 및 기사 메타데이터 보강
- 개인화 피드와 피드 통계 제공
- 소스 상태 및 모니터링 화면 제공

## 프로젝트 구조

- `frontend/`: Next.js 기반 사용자 인터페이스
- `backend/`: FastAPI 기반 API 서버
- `backend/data/`: SQLite 데이터 및 시드 파일
- `docs/presskit/`: 프로젝트 소개 문안과 인포그래픽

## 실행

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

기본 개발 주소:

- Frontend: `http://127.0.0.1:3000`
- Backend API: `http://127.0.0.1:8000`

## 수집 소스

기본 활성 소스:

- RSS: Drone Life, The Robot Report, MIT News AI, EASA
- 한국 RSS: ETNews AI, ETNews Drone/UAM
- 공개 연구 API: Crossref, Europe PMC

키가 있으면 활성화되는 소스:

- `NEWSAPI_KEY`
- `GNEWS_API_KEY`
- `KCI_API_KEY`
- `CROSSREF_MAILTO`

선택적으로 외국어 기사 자동 번역도 켤 수 있습니다.

- `OLLAMA_MODEL`
- `OLLAMA_URL`
- `PAPAGO_CLIENT_ID`
- `PAPAGO_CLIENT_SECRET`
- `LIBRETRANSLATE_URL`
- `LIBRETRANSLATE_API_KEY`

## 한국 소스

추가된 한국 수집 소스:

- `ETNews AI`
- `ETNews Drone/UAM`
- `KCI Korea Drone AI Papers`
- `NewsAPI Korea Major Media`
- `GNews Korea Major Media`

한국어 기사와 논문 제목도 잡을 수 있도록 드론/AI 키워드, 주제 분류, 하이라이트 추출 규칙을 보강했습니다.

대형 언론사 커버리지는 RSS보다 검색형 API가 현실적이라 아래 매체를 한국 전용 쿼리로 흡수하도록 구성했습니다.

- YTN
- 연합뉴스
- 한국경제
- 중앙일보

한국 논문 소스를 실제로 켜려면 `.env`에 `KCI_API_KEY`를 넣으면 됩니다.

예시:

```bash
KCI_API_KEY=your_real_key
```

`KCI_API_KEY`가 없으면 모니터 화면에서 `키 대기`로 표시됩니다.

## 번역

외국어 기사에 대해 한국어 번역본을 카드에 함께 표시할 수 있습니다.

- `Ollama` 모델이 있으면 우선 사용
- `Papago` 키가 있으면 우선 사용
- `Papago`가 없고 `LIBRETRANSLATE_URL`이 있으면 LibreTranslate 사용
- 번역이 없으면 원문 그대로 표시

예시:

```bash
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
```

또는:

```bash
PAPAGO_CLIENT_ID=your_client_id
PAPAGO_CLIENT_SECRET=your_client_secret
```

## API

- `GET /api/news`
- `GET /api/feed`
- `GET /api/feed/stats`
- `GET /api/subscriptions`
- `POST /api/subscriptions`
- `PATCH /api/subscriptions/{sub_id}`
- `DELETE /api/subscriptions/{sub_id}`
- `POST /api/subscriptions/{sub_id}/crawl`
- `POST /api/translate/{article_id}`
- `GET /api/sources`

## 배포

운영 배포용 파일을 포함합니다.

- `Dockerfile`
- `docker-compose.yml`
- `Caddyfile`
- `DEPLOY.md`

도메인 연결과 HTTPS 설정 절차는 `DEPLOY.md`에 정리했습니다.

## 소개 자료

- 프로젝트 소개 문서: `docs/presskit/project_intro_ko.md`
- 인포그래픽: `docs/presskit/briefwave_infographic.svg`
