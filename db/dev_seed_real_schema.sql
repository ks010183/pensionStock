-- =====================================================================
-- 개발/테스트용: 실제 DB 스키마(4개 테이블) 복제 + 샘플 데이터
-- 실제 etf_db 가 없는 환경(CI, 개발 샌드박스)에서 백엔드를 검증할 때 사용.
-- 실제 운영 환경에서는 절대 실행하지 말 것 (실데이터를 덮어쓰지는 않지만 불필요).
-- DDL 은 db/schema_dump.txt 의 SHOW CREATE TABLE 결과와 동일 구조.
-- =====================================================================
SET NAMES utf8mb4;
USE etf_db;

DROP TABLE IF EXISTS etf_integration;
DROP TABLE IF EXISTS datamart_etfholderkor;
DROP TABLE IF EXISTS datamart_etfsectorweightkor;
DROP TABLE IF EXISTS datamart_stockcategorykor;

CREATE TABLE etf_integration (
  symbol varchar(50) DEFAULT NULL,
  symbol_id bigint NOT NULL,
  name varchar(500) DEFAULT NULL,
  name_ko varchar(500) DEFAULT NULL,
  description varchar(2500) DEFAULT NULL,
  domicile varchar(500) DEFAULT NULL,
  sec_type varchar(500) DEFAULT NULL,
  first_trading_date date DEFAULT NULL,
  symbol_deleted_at datetime(6) DEFAULT NULL,
  status varchar(500) DEFAULT NULL,
  expense double DEFAULT NULL,
  detail_deleted_at datetime(6) DEFAULT NULL,
  bench_mark varchar(800) DEFAULT NULL,
  leverage_power double DEFAULT NULL,
  origin_etf varchar(10) DEFAULT NULL,
  is_inverse varchar(200) DEFAULT NULL,
  is_leveraged varchar(200) DEFAULT NULL,
  product_keyword varchar(450) DEFAULT NULL,
  etf_keyword varchar(300) DEFAULT NULL,
  pension varchar(200) DEFAULT NULL,
  mgmt_strategy varchar(200) DEFAULT NULL,
  expense_misc double DEFAULT NULL,
  expense_transaction double DEFAULT NULL,
  total_expense double DEFAULT NULL,
  fund_type varchar(20) DEFAULT NULL,
  tax_treatment varchar(20) DEFAULT NULL,
  index_replication varchar(20) DEFAULT NULL,
  marketcap double DEFAULT NULL,
  nav double DEFAULT NULL,
  divdend_yield double DEFAULT NULL,
  week52high double DEFAULT NULL,
  week52high_date varchar(50) DEFAULT NULL,
  week52low double DEFAULT NULL,
  week52low_date varchar(50) DEFAULT NULL,
  avg_10_volume double DEFAULT NULL,
  avg_20_volume double DEFAULT NULL,
  avg_40_volume double DEFAULT NULL,
  avg_60_volume double DEFAULT NULL,
  avg_120_volume double DEFAULT NULL,
  avg_10_amount double DEFAULT NULL,
  avg_20_amount double DEFAULT NULL,
  avg_40_amount double DEFAULT NULL,
  avg_60_amount double DEFAULT NULL,
  avg_120_amount double DEFAULT NULL,
  day_10_moving_avg double DEFAULT NULL,
  day_20_moving_avg double DEFAULT NULL,
  day_40_moving_avg double DEFAULT NULL,
  day_60_moving_avg double DEFAULT NULL,
  day_120_moving_avg double DEFAULT NULL,
  dumped_at datetime(6) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE datamart_etfholderkor (
  id varchar(100) NOT NULL,
  symbol varchar(50) NOT NULL,
  item_name varchar(100) DEFAULT NULL,
  weight_percentage double DEFAULT NULL,
  shares_number double DEFAULT NULL,
  market_value double DEFAULT NULL,
  created_at datetime(6) NOT NULL,
  asset varchar(100) DEFAULT NULL,
  dumped_at datetime(6) DEFAULT NULL,
  deleted_at datetime(6) DEFAULT NULL,
  updated_at datetime(6) DEFAULT NULL,
  PRIMARY KEY (id),
  KEY idx_h_symbol (symbol),
  KEY idx_h_item (item_name),
  KEY idx_h_asset (asset)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE datamart_etfsectorweightkor (
  id varchar(100) NOT NULL,
  symbol varchar(50) NOT NULL,
  sector_name varchar(100) DEFAULT NULL,
  weight_percentage double DEFAULT NULL,
  created_at datetime(6) NOT NULL,
  dumped_at datetime(6) DEFAULT NULL,
  deleted_at datetime(6) DEFAULT NULL,
  updated_at datetime(6) DEFAULT NULL,
  PRIMARY KEY (id),
  KEY idx_s_symbol (symbol),
  KEY idx_s_sector (sector_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE datamart_stockcategorykor (
  id varchar(100) NOT NULL,
  title varchar(300) NOT NULL,
  description varchar(500) NOT NULL,
  created_at datetime(6) NOT NULL,
  rep_symbol varchar(10) DEFAULT NULL,
  search_tag varchar(200) DEFAULT NULL,
  dumped_at datetime(6) DEFAULT NULL,
  symbol varchar(10) DEFAULT NULL,
  deleted_at datetime(6) DEFAULT NULL,
  updated_at datetime(6) DEFAULT NULL,
  PRIMARY KEY (id),
  KEY idx_c_title (title),
  KEY idx_c_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 샘플 ETF (etf_integration) — 실제 값 형태 재현 (pension='rp', 설명문형 sec_type 등)
-- ---------------------------------------------------------------------
INSERT INTO etf_integration
 (symbol, symbol_id, name, name_ko, sec_type, status, pension, fund_type, bench_mark,
  expense, total_expense, leverage_power, is_inverse, is_leveraged,
  etf_keyword, product_keyword, marketcap, nav, day_10_moving_avg, dumped_at)
VALUES
 ('069500', 1, 'KODEX 200', 'KODEX 200', ' means an exchange-traded fund.', 'active', 'rp', '주식형', '코스피 200',
  0.15, 0.1887, 1, ' is not an inverse product', ' is not a leveraged product',
  'KOSPI200@주가지수', 'KOSPI200지수 구성종목@시가총액', 27030262500000, 123879, 36500, NOW(6)),
 ('102780', 2, 'KODEX 삼성그룹', 'KODEX 삼성그룹', ' means an exchange-traded fund.', 'active', 'rp', '주식형', 'MKF 삼성그룹',
  0.25, 0.30, 1, ' is not an inverse product', ' is not a leveraged product',
  '삼성그룹@그룹주', '삼성그룹 계열사', 1700000000000, 11200, 11200, NOW(6)),
 ('364980', 3, 'TIGER TOP10', 'TIGER TOP10', ' means an exchange-traded fund.', 'active', 'rp', '주식형', 'FnGuide TOP10',
  0.15, 0.18, 1, ' is not an inverse product', ' is not a leveraged product',
  'TOP10@대형주', '시가총액 상위 10종목', 2100000000000, 14800, 14800, NOW(6)),
 ('091180', 4, 'KODEX 자동차', 'KODEX 자동차', ' means an exchange-traded fund.', 'active', 'rp', '주식형', 'KRX 자동차',
  0.45, 0.52, 1, ' is not an inverse product', ' is not a leveraged product',
  '자동차@완성차', 'KRX Autos 지수', 650000000000, 21800, 21800, NOW(6)),
 ('138540', 5, 'TIGER 현대차그룹+', 'TIGER 현대차그룹+', ' means an exchange-traded fund.', 'active', 'rp', '주식형', 'FnGuide 현대차그룹+',
  0.40, 0.46, 1, ' is not an inverse product', ' is not a leveraged product',
  '현대차그룹@그룹주', '현대차그룹 계열사', 320000000000, 24500, 24500, NOW(6)),
 ('305720', 6, 'KODEX 2차전지산업', 'KODEX 2차전지산업', ' means an exchange-traded fund.', 'active', 'rp', '주식형', 'FnGuide 2차전지',
  0.45, 0.52, 1, ' is not an inverse product', ' is not a leveraged product',
  '2차전지@배터리', '2차전지 산업', 900000000000, 9800, 9800, NOW(6)),
 ('091160', 7, 'KODEX 반도체', 'KODEX 반도체', ' means an exchange-traded fund.', 'active', 'rp', '주식형', 'KRX 반도체',
  0.45, 0.5149, 1, ' is not an inverse product', ' is not a leveraged product',
  'KRX Semicon 지수@반도체', 'GICS 반도체 섹터', 6628100000000, 157617, 43500, NOW(6)),
 ('365000', 8, 'TIGER 인터넷TOP10', 'TIGER 인터넷TOP10', ' means an exchange-traded fund.', 'active', 'rp', '주식형', 'FnGuide 인터넷',
  0.40, 0.46, 1, ' is not an inverse product', ' is not a leveraged product',
  '인터넷@플랫폼', '인터넷 플랫폼 기업', 280000000000, 7900, 7900, NOW(6)),
 ('244580', 9, 'KODEX 바이오', 'KODEX 바이오', ' means an exchange-traded fund.', 'active', 'rp', '주식형', 'FnGuide 바이오',
  0.45, 0.52, 1, ' is not an inverse product', ' is not a leveraged product',
  '바이오@제약', '바이오 헬스케어', 210000000000, 10900, 10900, NOW(6)),
 ('091170', 10, 'KODEX 은행', 'KODEX 은행', ' means an exchange-traded fund.', 'active', 'rp', '주식형', 'KRX 은행',
  0.30, 0.3337, 1, ' is not an inverse product', ' is not a leveraged product',
  'KRX Banks 지수@은행', '은행 섹터', 509958000000, 14840, 9400, NOW(6)),
 ('449450', 11, 'PLUS K방산', 'PLUS K방산', ' means an exchange-traded fund.', 'active', 'rp', '주식형', 'FnGuide K방산',
  0.45, 0.52, 1, ' is not an inverse product', ' is not a leveraged product',
  'K방산@방위산업', '방위산업 대표기업', 810000000000, 22300, 22300, NOW(6)),
 ('439870', 12, 'KODEX 단기채권PLUS', 'KODEX 단기채권PLUS', ' means an exchange-traded fund.', 'active', 'rp', '채권형', 'KAP 단기채권',
  0.05, 0.07, 1, ' is not an inverse product', ' is not a leveraged product',
  '단기채권@금리', '단기 국공채/은행채', 2800000000000, 103500, 103500, NOW(6)),
 ('114260', 13, 'KODEX 국고채3년', 'KODEX 국고채3년', ' means an exchange-traded fund.', 'active', 'rp', '채권형', 'KTB 지수',
  0.15, 0.17, 1, ' is not an inverse product', ' is not a leveraged product',
  '국고채@금리', '국고채 3년', 950000000000, 59800, 59800, NOW(6)),
 ('273130', 14, 'KODEX 종합채권(AA-이상)액티브', 'KODEX 종합채권(AA-이상)액티브', ' means an exchange-traded fund.', 'active', 'rp', '채권형', 'KAP 종합채권',
  0.07, 0.09, 1, ' is not an inverse product', ' is not a leveraged product',
  '종합채권@금리', 'AA-이상 채권', 2100000000000, 108200, 108200, NOW(6)),
 -- 엣지 케이스: 비-ETF (REIT) — 유니버스에서 제외되어야 함
 ('088260', 15, '이리츠코크렙', '이리츠코크렙', ' means a real estate investment trust (REIT).', 'active', 'rp', '', '',
  0, NULL, 1, ' is not an inverse product', ' is not a leveraged product', '구조조정 리츠', '', 234363883000, 0, 3885, NOW(6)),
 -- 엣지 케이스: 레버리지 ETF — 연금 유니버스에서 제외되어야 함 (pension 빈값)
 ('122630', 16, 'KODEX 레버리지', 'KODEX 레버리지', ' means an exchange-traded fund.', 'active', '', '주식형', '코스피 200',
  0.64, 0.70, 2, ' is not an inverse product', ' is a leveraged product', '레버리지', 'KOSPI200 2배', 2000000000000, 20000, 20000, NOW(6)),
 -- 엣지 케이스: 상장폐지 — 제외되어야 함
 ('999999', 17, 'DELISTED ETF', '상장폐지ETF', ' means an exchange-traded fund.', 'delisted', 'rp', '주식형', '',
  0.3, NULL, 1, ' is not an inverse product', ' is not a leveraged product', '', '', 0, 0, 1000, NOW(6));

-- ---------------------------------------------------------------------
-- 구성종목 (datamart_etfholderkor) — asset=종목티커, item_name=종목명
-- ---------------------------------------------------------------------
INSERT INTO datamart_etfholderkor
 (id, symbol, item_name, weight_percentage, shares_number, market_value, created_at, asset, dumped_at, updated_at)
VALUES
 -- KODEX 200
 (MD5('069500-005930'),'069500','삼성전자',28.50,100,1,NOW(6),'005930',NOW(6),NOW(6)),
 (MD5('069500-000660'),'069500','SK하이닉스',12.20,100,1,NOW(6),'000660',NOW(6),NOW(6)),
 (MD5('069500-005380'),'069500','현대차',3.80,100,1,NOW(6),'005380',NOW(6),NOW(6)),
 (MD5('069500-000270'),'069500','기아',2.90,100,1,NOW(6),'000270',NOW(6),NOW(6)),
 (MD5('069500-012330'),'069500','현대모비스',1.60,100,1,NOW(6),'012330',NOW(6),NOW(6)),
 (MD5('069500-373220'),'069500','LG에너지솔루션',3.40,100,1,NOW(6),'373220',NOW(6),NOW(6)),
 (MD5('069500-006400'),'069500','삼성SDI',1.50,100,1,NOW(6),'006400',NOW(6),NOW(6)),
 (MD5('069500-005490'),'069500','POSCO홀딩스',2.10,100,1,NOW(6),'005490',NOW(6),NOW(6)),
 (MD5('069500-035420'),'069500','NAVER',2.70,100,1,NOW(6),'035420',NOW(6),NOW(6)),
 (MD5('069500-035720'),'069500','카카오',1.30,100,1,NOW(6),'035720',NOW(6),NOW(6)),
 (MD5('069500-068270'),'069500','셀트리온',2.40,100,1,NOW(6),'068270',NOW(6),NOW(6)),
 (MD5('069500-207940'),'069500','삼성바이오로직스',3.60,100,1,NOW(6),'207940',NOW(6),NOW(6)),
 (MD5('069500-105560'),'069500','KB금융',3.10,100,1,NOW(6),'105560',NOW(6),NOW(6)),
 (MD5('069500-055550'),'069500','신한지주',2.50,100,1,NOW(6),'055550',NOW(6),NOW(6)),
 (MD5('069500-012450'),'069500','한화에어로스페이스',3.30,100,1,NOW(6),'012450',NOW(6),NOW(6)),
 (MD5('069500-028260'),'069500','삼성물산',1.90,100,1,NOW(6),'028260',NOW(6),NOW(6)),
 (MD5('069500-329180'),'069500','HD현대중공업',1.80,100,1,NOW(6),'329180',NOW(6),NOW(6)),
 (MD5('069500-047810'),'069500','한국항공우주',0.90,100,1,NOW(6),'047810',NOW(6),NOW(6)),
 -- KODEX 삼성그룹
 (MD5('102780-005930'),'102780','삼성전자',26.50,100,1,NOW(6),'005930',NOW(6),NOW(6)),
 (MD5('102780-207940'),'102780','삼성바이오로직스',16.80,100,1,NOW(6),'207940',NOW(6),NOW(6)),
 (MD5('102780-006400'),'102780','삼성SDI',12.40,100,1,NOW(6),'006400',NOW(6),NOW(6)),
 (MD5('102780-028260'),'102780','삼성물산',11.90,100,1,NOW(6),'028260',NOW(6),NOW(6)),
 -- TIGER TOP10
 (MD5('364980-005930'),'364980','삼성전자',24.80,100,1,NOW(6),'005930',NOW(6),NOW(6)),
 (MD5('364980-000660'),'364980','SK하이닉스',18.50,100,1,NOW(6),'000660',NOW(6),NOW(6)),
 (MD5('364980-373220'),'364980','LG에너지솔루션',8.90,100,1,NOW(6),'373220',NOW(6),NOW(6)),
 (MD5('364980-005380'),'364980','현대차',7.80,100,1,NOW(6),'005380',NOW(6),NOW(6)),
 (MD5('364980-207940'),'364980','삼성바이오로직스',7.10,100,1,NOW(6),'207940',NOW(6),NOW(6)),
 (MD5('364980-000270'),'364980','기아',6.40,100,1,NOW(6),'000270',NOW(6),NOW(6)),
 (MD5('364980-035420'),'364980','NAVER',6.00,100,1,NOW(6),'035420',NOW(6),NOW(6)),
 (MD5('364980-068270'),'364980','셀트리온',5.60,100,1,NOW(6),'068270',NOW(6),NOW(6)),
 (MD5('364980-105560'),'364980','KB금융',5.20,100,1,NOW(6),'105560',NOW(6),NOW(6)),
 (MD5('364980-012450'),'364980','한화에어로스페이스',5.10,100,1,NOW(6),'012450',NOW(6),NOW(6)),
 -- KODEX 자동차
 (MD5('091180-005380'),'091180','현대차',22.50,100,1,NOW(6),'005380',NOW(6),NOW(6)),
 (MD5('091180-000270'),'091180','기아',21.30,100,1,NOW(6),'000270',NOW(6),NOW(6)),
 (MD5('091180-012330'),'091180','현대모비스',12.80,100,1,NOW(6),'012330',NOW(6),NOW(6)),
 -- TIGER 현대차그룹+
 (MD5('138540-005380'),'138540','현대차',26.40,100,1,NOW(6),'005380',NOW(6),NOW(6)),
 (MD5('138540-000270'),'138540','기아',21.70,100,1,NOW(6),'000270',NOW(6),NOW(6)),
 (MD5('138540-012330'),'138540','현대모비스',14.20,100,1,NOW(6),'012330',NOW(6),NOW(6)),
 -- KODEX 2차전지산업
 (MD5('305720-373220'),'305720','LG에너지솔루션',18.20,100,1,NOW(6),'373220',NOW(6),NOW(6)),
 (MD5('305720-006400'),'305720','삼성SDI',14.60,100,1,NOW(6),'006400',NOW(6),NOW(6)),
 (MD5('305720-005490'),'305720','POSCO홀딩스',12.30,100,1,NOW(6),'005490',NOW(6),NOW(6)),
 -- KODEX 반도체
 (MD5('091160-000660'),'091160','SK하이닉스',22.40,100,1,NOW(6),'000660',NOW(6),NOW(6)),
 (MD5('091160-005930'),'091160','삼성전자',19.80,100,1,NOW(6),'005930',NOW(6),NOW(6)),
 -- TIGER 인터넷TOP10
 (MD5('365000-035420'),'365000','NAVER',26.30,100,1,NOW(6),'035420',NOW(6),NOW(6)),
 (MD5('365000-035720'),'365000','카카오',23.80,100,1,NOW(6),'035720',NOW(6),NOW(6)),
 -- KODEX 바이오
 (MD5('244580-068270'),'244580','셀트리온',19.60,100,1,NOW(6),'068270',NOW(6),NOW(6)),
 (MD5('244580-207940'),'244580','삼성바이오로직스',17.40,100,1,NOW(6),'207940',NOW(6),NOW(6)),
 -- KODEX 은행
 (MD5('091170-105560'),'091170','KB금융',24.10,100,1,NOW(6),'105560',NOW(6),NOW(6)),
 (MD5('091170-055550'),'091170','신한지주',22.60,100,1,NOW(6),'055550',NOW(6),NOW(6)),
 -- PLUS K방산
 (MD5('449450-012450'),'449450','한화에어로스페이스',24.20,100,1,NOW(6),'012450',NOW(6),NOW(6)),
 (MD5('449450-047810'),'449450','한국항공우주',16.90,100,1,NOW(6),'047810',NOW(6),NOW(6)),
 (MD5('449450-079550'),'449450','LIG넥스원',13.10,100,1,NOW(6),'079550',NOW(6),NOW(6)),
 (MD5('449450-000880'),'449450','한화',9.80,100,1,NOW(6),'000880',NOW(6),NOW(6)),
 -- 채권형 ETF: 비상장(asset='-1') 보유물 — 실데이터 형태 재현
 (MD5('439870-cd1'),'439870','국민은행(CD)',42.00,0,1,NOW(6),'-1',NOW(6),NOW(6)),
 (MD5('439870-bond1'),'439870','통안DC0129-0705-1820',40.00,0,1,NOW(6),'-1',NOW(6),NOW(6)),
 (MD5('114260-ktb'),'114260','국고03625-2809(25-6)',97.00,0,1,NOW(6),'-1',NOW(6),NOW(6)),
 (MD5('273130-b1'),'273130','국고02875-2612(16-8)',34.00,0,1,NOW(6),'-1',NOW(6),NOW(6)),
 (MD5('273130-b2'),'273130','한국전력채권1104',31.00,0,1,NOW(6),'-1',NOW(6),NOW(6)),
 -- 엣지 케이스: 소프트 삭제된 행 — 조회에서 제외되어야 함
 (MD5('069500-del'),'069500','삭제된종목',99.0,0,1,NOW(6),'000001',NOW(6),NOW(6));
UPDATE datamart_etfholderkor SET deleted_at = NOW(6) WHERE id = MD5('069500-del');

-- ---------------------------------------------------------------------
-- ETF 섹터 비중 (datamart_etfsectorweightkor)
-- ---------------------------------------------------------------------
INSERT INTO datamart_etfsectorweightkor
 (id, symbol, sector_name, weight_percentage, created_at, dumped_at, updated_at)
VALUES
 (MD5('s-069500-it'),'069500','IT',42.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-069500-fin'),'069500','금융',12.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-069500-ind'),'069500','산업재',15.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-091160-it'),'091160','IT',95.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-091180-auto'),'091180','경기소비재',88.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-138540-auto'),'138540','경기소비재',90.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-091170-fin'),'091170','금융',97.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-449450-ind'),'449450','산업재',93.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-364980-it'),'364980','IT',45.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-364980-health'),'364980','건강관리',13.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-244580-health'),'244580','건강관리',92.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-305720-it'),'305720','IT',55.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-305720-mat'),'305720','소재',30.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-365000-comm'),'365000','커뮤니케이션서비스',95.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-102780-it'),'102780','IT',50.0,NOW(6),NOW(6),NOW(6)),
 (MD5('s-439870-cash'),'439870','현금',10.0,NOW(6),NOW(6),NOW(6));

-- ---------------------------------------------------------------------
-- 테마 (datamart_stockcategorykor) — title=테마명, symbol=관련 티커 (테마→심볼 N행)
-- ---------------------------------------------------------------------
INSERT INTO datamart_stockcategorykor
 (id, title, description, created_at, rep_symbol, search_tag, dumped_at, symbol, updated_at)
VALUES
 (MD5('t-ai-1'),'인공지능','AI 반도체/플랫폼','2026-06-12','091160','인공지능@AI@반도체',NOW(6),'091160',NOW(6)),
 (MD5('t-ai-2'),'인공지능','AI 반도체/플랫폼','2026-06-12','091160','인공지능@AI@반도체',NOW(6),'365000',NOW(6)),
 (MD5('t-semi-1'),'반도체','반도체 산업','2026-06-12','091160','반도체@메모리@파운드리',NOW(6),'091160',NOW(6)),
 (MD5('t-semi-2'),'반도체','반도체 산업','2026-06-12','091160','반도체@메모리@파운드리',NOW(6),'069500',NOW(6)),
 (MD5('t-defense-1'),'방위산업','K-방산','2026-06-12','449450','방산@K방산@방위산업',NOW(6),'449450',NOW(6)),
 (MD5('t-ev-1'),'2차전지','전기차 배터리','2026-06-12','305720','2차전지@배터리@전기차',NOW(6),'305720',NOW(6)),
 (MD5('t-ev-2'),'전기차','전기차 밸류체인','2026-06-12','091180','전기차@EV@자율주행',NOW(6),'091180',NOW(6)),
 (MD5('t-ev-3'),'전기차','전기차 밸류체인','2026-06-12','091180','전기차@EV@자율주행',NOW(6),'138540',NOW(6)),
 (MD5('t-bank-1'),'은행','은행/금융지주','2026-06-12','091170','은행@금융@배당',NOW(6),'091170',NOW(6)),
 (MD5('t-bio-1'),'바이오','제약/바이오','2026-06-12','244580','바이오@제약@헬스케어',NOW(6),'244580',NOW(6)),
 (MD5('t-grp-1'),'삼성그룹','삼성그룹주','2026-06-12','102780','삼성그룹@그룹주',NOW(6),'102780',NOW(6)),
 (MD5('t-grp-2'),'현대차그룹','현대차그룹주','2026-06-12','138540','현대차그룹@그룹주',NOW(6),'138540',NOW(6)),
 (MD5('t-rate-1'),'금리','금리/채권','2026-06-12','439870','금리@채권@단기자금',NOW(6),'439870',NOW(6)),
 (MD5('t-rate-2'),'금리','금리/채권','2026-06-12','439870','금리@채권@단기자금',NOW(6),'114260',NOW(6));

-- ---------------------------------------------------------------------
-- 심볼 마스터 (datamart_symbolkor / datamart_symbolus) — fuzzy 검색용
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS datamart_symbolkor;
DROP TABLE IF EXISTS datamart_symbolus;

CREATE TABLE datamart_symbolkor (
  id bigint NOT NULL AUTO_INCREMENT PRIMARY KEY,
  symbol varchar(50) UNIQUE,
  name varchar(500),
  name_ko varchar(500),
  order_rank int,
  tag varchar(200),
  description_ko varchar(2500),
  cusip varchar(50),
  isin varchar(50),
  domicile varchar(500),
  sec_type varchar(500),
  first_trading_date date,
  created_at datetime(6),
  updated_at datetime(6),
  deleted_at datetime(6),
  status varchar(500),
  dumped_at datetime(6),
  KEY idx_sk_name (name),
  KEY idx_sk_name_ko (name_ko)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE datamart_symbolus LIKE datamart_symbolkor;

INSERT INTO datamart_symbolkor (symbol, name, name_ko, order_rank, sec_type, status) VALUES
 ('005930','삼성전자','삼성전자',1,' is a general stock symbol and stock ticker.','active'),
 ('000660','SK하이닉스','SK하이닉스',2,' is a general stock symbol and stock ticker.','active'),
 ('005380','현대차','현대차',3,' is a general stock symbol and stock ticker.','active'),
 ('000270','기아','기아',4,' is a general stock symbol and stock ticker.','active'),
 ('012330','현대모비스','현대모비스',8,' is a general stock symbol and stock ticker.','active'),
 ('373220','LG에너지솔루션','LG에너지솔루션',5,' is a general stock symbol and stock ticker.','active'),
 ('006400','삼성SDI','삼성SDI',9,' is a general stock symbol and stock ticker.','active'),
 ('005490','POSCO홀딩스','POSCO홀딩스',7,' is a general stock symbol and stock ticker.','active'),
 ('035420','NAVER','NAVER',6,' is a general stock symbol and stock ticker.','active'),
 ('035720','카카오','카카오',10,' is a general stock symbol and stock ticker.','active'),
 ('068270','셀트리온','셀트리온',11,' is a general stock symbol and stock ticker.','active'),
 ('207940','삼성바이오로직스','삼성바이오로직스',12,' is a general stock symbol and stock ticker.','active'),
 ('105560','KB금융','KB금융',13,' is a general stock symbol and stock ticker.','active'),
 ('055550','신한지주','신한지주',14,' is a general stock symbol and stock ticker.','active'),
 ('012450','한화에어로스페이스','한화에어로스페이스',15,' is a general stock symbol and stock ticker.','active'),
 ('047810','한국항공우주','한국항공우주',20,' is a general stock symbol and stock ticker.','active'),
 ('079550','LIG넥스원','LIG넥스원',21,' is a general stock symbol and stock ticker.','active'),
 ('000880','한화','한화',22,' is a general stock symbol and stock ticker.','active'),
 ('028260','삼성물산','삼성물산',18,' is a general stock symbol and stock ticker.','active'),
 ('329180','HD현대중공업','HD현대중공업',19,' is a general stock symbol and stock ticker.','active'),
 ('069500','KODEX 200','KODEX 200',1,' means an exchange-traded fund.','active'),
 ('091160','KODEX 반도체','KODEX 반도체',5,' means an exchange-traded fund.','active'),
 ('102780','KODEX 삼성그룹','KODEX 삼성그룹',7,' means an exchange-traded fund.','active'),
 ('305720','KODEX 2차전지산업','KODEX 2차전지산업',8,' means an exchange-traded fund.','active'),
 ('449450','PLUS K방산','PLUS K방산',9,' means an exchange-traded fund.','active'),
 ('439870','KODEX 단기채권PLUS','KODEX 단기채권PLUS',10,' means an exchange-traded fund.','active'),
 ('580011','삼성 인버스 2X WTI원유 선물 ETN','삼성 인버스 2X WTI원유 선물 ETN',0,' means an exchange-traded note.','active'),
 ('000060','메리츠화재','메리츠화재',0,' is a general stock symbol and stock ticker.','inactive');
UPDATE datamart_symbolkor SET deleted_at=NOW(6) WHERE symbol='000060';

INSERT INTO datamart_symbolus (symbol, name, name_ko, order_rank, sec_type, status) VALUES
 ('AAPL','Apple Inc.','애플',1,' is a general stock symbol and stock ticker.','active'),
 ('TSLA','Tesla, Inc.','테슬라',2,' is a general stock symbol and stock ticker.','active'),
 ('NVDA','NVIDIA Corporation','엔비디아',1,' is a general stock symbol and stock ticker.','active'),
 ('TTD','Trade Desk, Inc. Class A','트레이드 데스크',3,' is a general stock symbol and stock ticker.','active'),
 ('SPY','SPDR S&P 500 ETF Trust','SPDR S&P500',1,' means an exchange-traded fund.','active'),
 ('TSLL','Direxion Daily TSLA Bull 2X Shares','테슬라 2X 불',5,' means it is a type of ETFs whose underlying asset is a single stock.','active');
