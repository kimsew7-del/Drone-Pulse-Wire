# Deploy

이 프로젝트는 별도 패키지 설치 없이 Python 표준 라이브러리로 동작합니다. 운영 배포는 `Dockerfile` + `docker-compose.yml` + `Caddyfile` 기준으로 맞춰져 있습니다.

## 1. 서버 준비

- Ubuntu VPS 1대
- 도메인 1개
- 서버 공개 IP 확보
- 방화벽에서 `80`, `443` 오픈

## 2. 도메인 연결

DNS에서 아래처럼 설정합니다.

- `A @ -> 서버 공인 IP`
- `A www -> 서버 공인 IP`

## 3. 환경 변수

`.env.example`를 복사해 `.env`를 만듭니다.

```bash
cp .env.example .env
```

운영에서 권장하는 값:

- `HOST=0.0.0.0`
- `PORT=8080`
- `NEWSAPI_KEY=...`
- `GNEWS_API_KEY=...`
- `KCI_API_KEY=...`
- `CROSSREF_MAILTO=you@example.com`

## 4. Caddy 도메인 수정

`Caddyfile`의 첫 줄을 실제 도메인으로 바꿉니다.

```caddy
your-domain.com, www.your-domain.com {
  encode gzip
  reverse_proxy app:8080
}
```

Caddy는 유효한 DNS가 잡혀 있으면 자동으로 HTTPS 인증서를 발급합니다.

## 5. 실행

```bash
docker compose up -d --build
```

## 6. 확인

- 메인 피드: `https://your-domain.com`
- 소스 모니터: `https://your-domain.com/monitor.html`
- API: `https://your-domain.com/api/news`

## 7. 운영 팁

- 수집 상태는 `data/runtime_state.json`에 저장됩니다.
- `KCI_API_KEY`가 없으면 한국 논문 소스는 `키 대기`로 표시됩니다.
- `NEWSAPI_KEY`, `GNEWS_API_KEY`가 없으면 해당 상용 뉴스 소스는 비활성 상태로 유지됩니다.
