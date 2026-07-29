#!/usr/bin/env bash
# 실제 ETF DB(로컬 Docker MySQL)의 4개 테이블 스키마/샘플을 db/schema_dump.txt 로 덤프
# 사용법:
#   ./db/inspect_schema.sh              # mysql/mariadb 컨테이너 자동 탐지
#   ./db/inspect_schema.sh <컨테이너명>  # 직접 지정
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
CONTAINER="${1:-$(docker ps --format '{{.Names}}\t{{.Image}}' | grep -i -m1 -E 'mysql|maria' | cut -f1)}"

if [ -z "$CONTAINER" ]; then
  echo "MySQL 컨테이너를 찾지 못했습니다. ./db/inspect_schema.sh <컨테이너명> 으로 지정하세요."
  docker ps --format '  - {{.Names}} ({{.Image}})'
  exit 1
fi

echo "컨테이너: $CONTAINER"
docker exec -i "$CONTAINER" mysql -uroot -pmysql --default-character-set=utf8mb4 etf_db \
  < "$DIR/inspect_schema.sql" > "$DIR/schema_dump.txt" 2>&1 || true

if grep -qi "error" "$DIR/schema_dump.txt" && ! grep -q "COLUMNS" "$DIR/schema_dump.txt"; then
  echo "오류가 발생했습니다 — db/schema_dump.txt 내용을 확인하세요:"
  head -5 "$DIR/schema_dump.txt"
  exit 1
fi

echo "완료: db/schema_dump.txt ($(wc -l < "$DIR/schema_dump.txt") lines)"
