-- datamart_symbolkor / datamart_symbolus 스키마·샘플 덤프 (symbols_dump.txt 생성용)
SET NAMES utf8mb4;
USE etf_db;

SELECT '##### COLUMNS #####' AS marker;
SELECT TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_COMMENT
FROM information_schema.columns
WHERE table_schema='etf_db' AND table_name IN ('datamart_symbolkor','datamart_symbolus')
ORDER BY TABLE_NAME, ORDINAL_POSITION;

SELECT '##### ROW COUNTS #####' AS marker;
SELECT 'datamart_symbolkor' t, COUNT(*) c FROM datamart_symbolkor
UNION ALL SELECT 'datamart_symbolus', COUNT(*) FROM datamart_symbolus;

SELECT '##### sec_type 분포: symbolkor #####' AS marker;
SELECT sec_type, COUNT(*) c FROM datamart_symbolkor GROUP BY sec_type ORDER BY c DESC LIMIT 20;

SELECT '##### sec_type 분포: symbolus #####' AS marker;
SELECT sec_type, COUNT(*) c FROM datamart_symbolus GROUP BY sec_type ORDER BY c DESC LIMIT 20;

SELECT '##### SAMPLE: symbolkor (삼성전자 검색) #####' AS marker;
SELECT * FROM datamart_symbolkor WHERE symbol='005930' OR symbol LIKE '%005930%' LIMIT 3\G
SELECT '##### SAMPLE: symbolkor 5행 #####' AS marker;
SELECT * FROM datamart_symbolkor LIMIT 5\G
SELECT '##### SAMPLE: symbolus 5행 #####' AS marker;
SELECT * FROM datamart_symbolus LIMIT 5\G
