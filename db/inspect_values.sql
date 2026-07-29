-- RISK/SAFE 분류·연금 필터 규칙 검증용 값 분포 덤프 (values_dump.txt 생성용)
SET NAMES utf8mb4;
USE etf_db;

SELECT '##### pension 분포 #####' AS marker;
SELECT pension, COUNT(*) AS cnt FROM etf_integration GROUP BY pension ORDER BY cnt DESC;

SELECT '##### fund_type 분포 #####' AS marker;
SELECT fund_type, COUNT(*) AS cnt FROM etf_integration GROUP BY fund_type ORDER BY cnt DESC;

SELECT '##### sec_type 분포 #####' AS marker;
SELECT sec_type, COUNT(*) AS cnt FROM etf_integration GROUP BY sec_type ORDER BY cnt DESC;

SELECT '##### status 분포 #####' AS marker;
SELECT status, COUNT(*) AS cnt FROM etf_integration GROUP BY status ORDER BY cnt DESC;

SELECT '##### tax_treatment 분포 #####' AS marker;
SELECT tax_treatment, COUNT(*) AS cnt FROM etf_integration GROUP BY tax_treatment ORDER BY cnt DESC;

SELECT '##### leverage/inverse 분포 #####' AS marker;
SELECT leverage_power, is_leveraged, is_inverse, COUNT(*) AS cnt
FROM etf_integration GROUP BY leverage_power, is_leveraged, is_inverse ORDER BY cnt DESC;

SELECT '##### 연금 유니버스 통과 상품 수 #####' AS marker;
SELECT COUNT(*) AS universe_cnt FROM etf_integration e
WHERE e.status='active' AND e.symbol_deleted_at IS NULL
  AND e.sec_type LIKE '%exchange-traded fund%'
  AND COALESCE(e.leverage_power,1)=1
  AND (e.is_inverse IS NULL OR e.is_inverse LIKE '%not an inverse%')
  AND (e.is_leveraged IS NULL OR e.is_leveraged LIKE '%not a leveraged%')
  AND COALESCE(e.pension,'') <> '';

SELECT '##### fund_type=채권형 예시 20건 #####' AS marker;
SELECT symbol, name_ko, fund_type, bench_mark FROM etf_integration
WHERE fund_type LIKE '%채권%' OR fund_type LIKE '%금리%' OR fund_type LIKE '%단기%'
LIMIT 20;

SELECT '##### 가격정보 없는 상품 수 (day_10_moving_avg, nav 모두 NULL/0) #####' AS marker;
SELECT COUNT(*) AS no_price_cnt FROM etf_integration
WHERE COALESCE(day_10_moving_avg,0)=0 AND COALESCE(nav,0)=0;

SELECT '##### 테마 심볼 유형 확인 (theme symbol 이 ETF 인 비율) #####' AS marker;
SELECT
  SUM(CASE WHEN e.symbol IS NOT NULL THEN 1 ELSE 0 END) AS symbol_is_etf,
  COUNT(*) AS total
FROM datamart_stockcategorykor c
LEFT JOIN etf_integration e ON e.symbol = c.symbol
WHERE c.deleted_at IS NULL AND c.symbol IS NOT NULL;
