# Briefwave

드론과 AI 관련 글로벌/한국 뉴스를 피드 형태로 자동 적재하고, 트렌드와 신기술 리포트를 함께 보여주는 앱입니다.

## 실행

```bash
python3 server.py
```

더 간단히 실행하려면:

```bash
./run_local.sh
```

처음 실행 시 `.env`가 없으면 `.env.example` 기준으로 자동 생성합니다.

기본 접속 주소:

- 메인 피드: `http://127.0.0.1:8080`
- 소스 모니터: `http://127.0.0.1:8080/monitor.html`

## 현재 구성

- `index.html`: 메인 피드
- `monitor.html`: 소스 상태 모니터링 화면
- `app.js`: 피드, 트렌드, 리포트, 카드 액션 렌더링
- `monitor.js`: 소스 상태 전용 대시보드
- `server.py`: 정적 파일 + API 서버
- `backend/news_service.py`: 수집, 정규화, 중복 제거, 트렌드 스냅샷

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
- `POST /api/refresh`
- `GET /api/sources`

`/api/news`에는 아래가 포함됩니다.

- 기사 목록
- 소스 상태
- 라이브 시그널
- 최근 트렌드 스냅샷 히스토리

## 배포

운영 배포용 파일을 포함합니다.

- `Dockerfile`
- `docker-compose.yml`
- `Caddyfile`
- `DEPLOY.md`

도메인 연결과 HTTPS 설정 절차는 [DEPLOY.md](/Users/daon/projects/Drone_news/DEPLOY.md)에 정리했습니다.
