#!/bin/zsh

set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env 파일이 없어 기본 템플릿으로 생성했습니다."
fi

python3 server.py
