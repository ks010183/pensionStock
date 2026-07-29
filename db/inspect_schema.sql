-- 실제 ETF DB 4개 테이블 스키마/샘플 덤프 (schema_dump.txt 생성용)
SET NAMES utf8mb4;
USE etf_db;

SELECT '##### COLUMNS #####' AS marker;
SELECT TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE,
       COLUMN_KEY, COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT
FROM information_schema.columns
WHERE table_schema = 'etf_db'
  AND table_name IN ('etf_integration', 'datamart_etfholderkor',
                     'datamart_etfsectorweightkor', 'datamart_stockcategorykor')
ORDER BY TABLE_NAME, ORDINAL_POSITION;

SELECT '##### INDEXES #####' AS marker;
SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME
FROM information_schema.statistics
WHERE table_schema = 'etf_db'
  AND table_name IN ('etf_integration', 'datamart_etfholderkor',
                     'datamart_etfsectorweightkor', 'datamart_stockcategorykor')
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

SELECT '##### CREATE: etf_integration #####' AS marker;
SHOW CREATE TABLE etf_integration\G
SELECT '##### CREATE: datamart_etfholderkor #####' AS marker;
SHOW CREATE TABLE datamart_etfholderkor\G
SELECT '##### CREATE: datamart_etfsectorweightkor #####' AS marker;
SHOW CREATE TABLE datamart_etfsectorweightkor\G
SELECT '##### CREATE: datamart_stockcategorykor #####' AS marker;
SHOW CREATE TABLE datamart_stockcategorykor\G

SELECT '##### ROW COUNTS #####' AS marker;
SELECT 'etf_integration' AS table_name, COUNT(*) AS rows_cnt FROM etf_integration
UNION ALL SELECT 'datamart_etfholderkor', COUNT(*) FROM datamart_etfholderkor
UNION ALL SELECT 'datamart_etfsectorweightkor', COUNT(*) FROM datamart_etfsectorweightkor
UNION ALL SELECT 'datamart_stockcategorykor', COUNT(*) FROM datamart_stockcategorykor;

SELECT '##### SAMPLE: etf_integration #####' AS marker;
SELECT * FROM etf_integration LIMIT 5\G
SELECT '##### SAMPLE: datamart_etfholderkor #####' AS marker;
SELECT * FROM datamart_etfholderkor LIMIT 5\G
SELECT '##### SAMPLE: datamart_etfsectorweightkor #####' AS marker;
SELECT * FROM datamart_etfsectorweightkor LIMIT 5\G
SELECT '##### SAMPLE: datamart_stockcategorykor #####' AS marker;
SELECT * FROM datamart_stockcategorykor LIMIT 5\G
