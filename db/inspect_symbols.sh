#!/usr/bin/env bash
# datamart_symbolkor / datamart_symbolus 스키마를 db/symbols_dump.txt 로 덤프
# 사용법: ./db/inspect_symbols.sh [컨테이너명]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
CONTAINER="${1:-$(docker ps --format '{{.Names}}\t{{.Image}}' | grep -i -m1 -E 'mysql|maria' | cut -f1)}"

if [ -z "$CONTAINER" ]; then
  echo "MySQL 컨테이너를 찾지 못했습니다. ./db/inspect_symbols.sh <컨테이너명> 으로 지정하세요."
  exit 1
fi

echo "컨테이너: $CONTAINER"
docker exec -i "$CONTAINER" mysql -uroot -pmysql --default-character-set=utf8mb4 etf_db \
  < "$DIR/inspect_symbols.sql" > "$DIR/symbols_dump.txt" 2>&1 || true
echo "완료: db/symbols_dump.txt ($(wc -l < "$DIR/symbols_dump.txt") lines)"
