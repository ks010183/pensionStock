#!/usr/bin/env bash
# RISK/SAFE 분류·연금 필터 규칙 검증용 값 분포를 db/values_dump.txt 로 덤프
# 사용법: ./db/inspect_values.sh [컨테이너명]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
CONTAINER="${1:-$(docker ps --format '{{.Names}}\t{{.Image}}' | grep -i -m1 -E 'mysql|maria' | cut -f1)}"

if [ -z "$CONTAINER" ]; then
  echo "MySQL 컨테이너를 찾지 못했습니다. ./db/inspect_values.sh <컨테이너명> 으로 지정하세요."
  exit 1
fi

echo "컨테이너: $CONTAINER"
docker exec -i "$CONTAINER" mysql -uroot -pmysql --default-character-set=utf8mb4 etf_db \
  < "$DIR/inspect_values.sql" > "$DIR/values_dump.txt" 2>&1 || true
echo "완료: db/values_dump.txt ($(wc -l < "$DIR/values_dump.txt") lines)"
