-- =========================================================
-- ETF 샘플 시드 데이터 (국내 ETF 예시 — 데모용 근사 데이터)
-- =========================================================
SET NAMES utf8mb4;
USE etf_db;

-- 국가
INSERT INTO countries VALUES ('KR','대한민국'),('US','미국');

-- 섹터
INSERT INTO sectors (sector_name) VALUES
 ('반도체'),('자동차'),('2차전지'),('인터넷/플랫폼'),('바이오/헬스케어'),
 ('금융'),('방위산업'),('철강/소재'),('조선/기계'),('지주회사'),('채권');

-- 테마
INSERT INTO themes (theme_name) VALUES
 ('AI'),('반도체'),('전기차'),('2차전지'),('자율주행'),('K-방산'),
 ('플랫폼'),('바이오'),('배당'),('삼성그룹'),('현대차그룹'),('우주항공'),('금리'),('안전자산');

-- 주식 종목 (섹터: 이름으로 서브쿼리)
INSERT INTO stocks (stock_code, stock_name, sector_id, country_code) VALUES
 ('005930','삼성전자',        (SELECT sector_id FROM sectors WHERE sector_name='반도체'),'KR'),
 ('000660','SK하이닉스',      (SELECT sector_id FROM sectors WHERE sector_name='반도체'),'KR'),
 ('005380','현대차',          (SELECT sector_id FROM sectors WHERE sector_name='자동차'),'KR'),
 ('000270','기아',            (SELECT sector_id FROM sectors WHERE sector_name='자동차'),'KR'),
 ('012330','현대모비스',      (SELECT sector_id FROM sectors WHERE sector_name='자동차'),'KR'),
 ('373220','LG에너지솔루션',  (SELECT sector_id FROM sectors WHERE sector_name='2차전지'),'KR'),
 ('006400','삼성SDI',         (SELECT sector_id FROM sectors WHERE sector_name='2차전지'),'KR'),
 ('005490','POSCO홀딩스',     (SELECT sector_id FROM sectors WHERE sector_name='철강/소재'),'KR'),
 ('035420','NAVER',           (SELECT sector_id FROM sectors WHERE sector_name='인터넷/플랫폼'),'KR'),
 ('035720','카카오',          (SELECT sector_id FROM sectors WHERE sector_name='인터넷/플랫폼'),'KR'),
 ('068270','셀트리온',        (SELECT sector_id FROM sectors WHERE sector_name='바이오/헬스케어'),'KR'),
 ('207940','삼성바이오로직스',(SELECT sector_id FROM sectors WHERE sector_name='바이오/헬스케어'),'KR'),
 ('105560','KB금융',          (SELECT sector_id FROM sectors WHERE sector_name='금융'),'KR'),
 ('055550','신한지주',        (SELECT sector_id FROM sectors WHERE sector_name='금융'),'KR'),
 ('012450','한화에어로스페이스',(SELECT sector_id FROM sectors WHERE sector_name='방위산업'),'KR'),
 ('047810','한국항공우주',    (SELECT sector_id FROM sectors WHERE sector_name='방위산업'),'KR'),
 ('079550','LIG넥스원',       (SELECT sector_id FROM sectors WHERE sector_name='방위산업'),'KR'),
 ('000880','한화',            (SELECT sector_id FROM sectors WHERE sector_name='지주회사'),'KR'),
 ('028260','삼성물산',        (SELECT sector_id FROM sectors WHERE sector_name='지주회사'),'KR'),
 ('329180','HD현대중공업',    (SELECT sector_id FROM sectors WHERE sector_name='조선/기계'),'KR'),
 ('KRBOND01','국고채 3년',    (SELECT sector_id FROM sectors WHERE sector_name='채권'),'KR'),
 ('KRBOND02','국고채 10년',   (SELECT sector_id FROM sectors WHERE sector_name='채권'),'KR'),
 ('KRBOND03','통안채/단기채', (SELECT sector_id FROM sectors WHERE sector_name='채권'),'KR'),
 ('KRBOND04','우량 회사채',   (SELECT sector_id FROM sectors WHERE sector_name='채권'),'KR');

-- 주식-테마 매핑
INSERT INTO stock_themes (stock_code, theme_id) VALUES
 ('005930',(SELECT theme_id FROM themes WHERE theme_name='AI')),
 ('005930',(SELECT theme_id FROM themes WHERE theme_name='반도체')),
 ('005930',(SELECT theme_id FROM themes WHERE theme_name='삼성그룹')),
 ('000660',(SELECT theme_id FROM themes WHERE theme_name='AI')),
 ('000660',(SELECT theme_id FROM themes WHERE theme_name='반도체')),
 ('005380',(SELECT theme_id FROM themes WHERE theme_name='전기차')),
 ('005380',(SELECT theme_id FROM themes WHERE theme_name='자율주행')),
 ('005380',(SELECT theme_id FROM themes WHERE theme_name='현대차그룹')),
 ('000270',(SELECT theme_id FROM themes WHERE theme_name='전기차')),
 ('000270',(SELECT theme_id FROM themes WHERE theme_name='현대차그룹')),
 ('012330',(SELECT theme_id FROM themes WHERE theme_name='자율주행')),
 ('012330',(SELECT theme_id FROM themes WHERE theme_name='현대차그룹')),
 ('373220',(SELECT theme_id FROM themes WHERE theme_name='2차전지')),
 ('373220',(SELECT theme_id FROM themes WHERE theme_name='전기차')),
 ('006400',(SELECT theme_id FROM themes WHERE theme_name='2차전지')),
 ('006400',(SELECT theme_id FROM themes WHERE theme_name='삼성그룹')),
 ('005490',(SELECT theme_id FROM themes WHERE theme_name='2차전지')),
 ('035420',(SELECT theme_id FROM themes WHERE theme_name='플랫폼')),
 ('035420',(SELECT theme_id FROM themes WHERE theme_name='AI')),
 ('035720',(SELECT theme_id FROM themes WHERE theme_name='플랫폼')),
 ('068270',(SELECT theme_id FROM themes WHERE theme_name='바이오')),
 ('207940',(SELECT theme_id FROM themes WHERE theme_name='바이오')),
 ('207940',(SELECT theme_id FROM themes WHERE theme_name='삼성그룹')),
 ('105560',(SELECT theme_id FROM themes WHERE theme_name='배당')),
 ('055550',(SELECT theme_id FROM themes WHERE theme_name='배당')),
 ('012450',(SELECT theme_id FROM themes WHERE theme_name='K-방산')),
 ('012450',(SELECT theme_id FROM themes WHERE theme_name='우주항공')),
 ('047810',(SELECT theme_id FROM themes WHERE theme_name='K-방산')),
 ('047810',(SELECT theme_id FROM themes WHERE theme_name='우주항공')),
 ('079550',(SELECT theme_id FROM themes WHERE theme_name='K-방산')),
 ('000880',(SELECT theme_id FROM themes WHERE theme_name='K-방산')),
 ('028260',(SELECT theme_id FROM themes WHERE theme_name='삼성그룹')),
 ('KRBOND01',(SELECT theme_id FROM themes WHERE theme_name='금리')),
 ('KRBOND01',(SELECT theme_id FROM themes WHERE theme_name='안전자산')),
 ('KRBOND02',(SELECT theme_id FROM themes WHERE theme_name='금리')),
 ('KRBOND03',(SELECT theme_id FROM themes WHERE theme_name='안전자산')),
 ('KRBOND04',(SELECT theme_id FROM themes WHERE theme_name='안전자산'));

-- ETF 기본 (asset_class: RISK=위험자산, SAFE=안전자산)
INSERT INTO etfs (etf_code, etf_name, issuer, asset_class, expense_ratio, close_price, aum, country_code) VALUES
 ('069500','KODEX 200',            '삼성자산운용',   'RISK',0.1500, 36500, 65000,'KR'),
 ('102780','KODEX 삼성그룹',       '삼성자산운용',   'RISK',0.2500, 11200,  17000,'KR'),
 ('364980','TIGER TOP10',          '미래에셋자산운용','RISK',0.1500, 14800, 21000,'KR'),
 ('091180','KODEX 자동차',         '삼성자산운용',   'RISK',0.4500, 21800,  6500,'KR'),
 ('138540','TIGER 현대차그룹+',    '미래에셋자산운용','RISK',0.4000, 24500,  3200,'KR'),
 ('305720','KODEX 2차전지산업',    '삼성자산운용',   'RISK',0.4500,  9800,  9000,'KR'),
 ('091160','KODEX 반도체',         '삼성자산운용',   'RISK',0.4500, 43500, 12000,'KR'),
 ('365000','TIGER 인터넷TOP10',    '미래에셋자산운용','RISK',0.4000,  7900,  2800,'KR'),
 ('244580','KODEX 바이오',         '삼성자산운용',   'RISK',0.4500, 10900,  2100,'KR'),
 ('091170','KODEX 은행',           '삼성자산운용',   'RISK',0.3000,  9400,  3900,'KR'),
 ('449450','PLUS K방산',           '한화자산운용',   'RISK',0.4500, 22300,  8100,'KR'),
 ('466920','SOL 조선TOP3플러스',   '신한자산운용',   'RISK',0.4500, 15300,  4700,'KR'),
 ('439870','KODEX 단기채권PLUS',   '삼성자산운용',   'SAFE',0.0500,103500, 28000,'KR'),
 ('114260','KODEX 국고채3년',      '삼성자산운용',   'SAFE',0.1500, 59800,  9500,'KR'),
 ('273130','KODEX 종합채권(AA-이상)','삼성자산운용', 'SAFE',0.0700,108200, 21000,'KR');

-- ETF 구성종목 (비중 %, 데모용 근사치 — 합계는 100 이하, 잔여분은 현금/기타로 간주)
-- KODEX 200
INSERT INTO etf_holdings VALUES
 ('069500','005930',28.50),('069500','000660',12.20),('069500','005380',3.80),
 ('069500','000270',2.90),('069500','012330',1.60),('069500','373220',3.40),
 ('069500','006400',1.50),('069500','005490',2.10),('069500','035420',2.70),
 ('069500','035720',1.30),('069500','068270',2.40),('069500','207940',3.60),
 ('069500','105560',3.10),('069500','055550',2.50),('069500','012450',3.30),
 ('069500','028260',1.90),('069500','329180',1.80),('069500','047810',0.90);

-- KODEX 삼성그룹
INSERT INTO etf_holdings VALUES
 ('102780','005930',26.50),('102780','207940',16.80),('102780','006400',12.40),
 ('102780','028260',11.90);

-- TIGER TOP10
INSERT INTO etf_holdings VALUES
 ('364980','005930',24.80),('364980','000660',18.50),('364980','373220',8.90),
 ('364980','005380',7.80),('364980','207940',7.10),('364980','000270',6.40),
 ('364980','035420',6.00),('364980','068270',5.60),('364980','105560',5.20),
 ('364980','012450',5.10);

-- KODEX 자동차
INSERT INTO etf_holdings VALUES
 ('091180','005380',22.50),('091180','000270',21.30),('091180','012330',12.80);

-- TIGER 현대차그룹+
INSERT INTO etf_holdings VALUES
 ('138540','005380',26.40),('138540','000270',21.70),('138540','012330',14.20);

-- KODEX 2차전지산업
INSERT INTO etf_holdings VALUES
 ('305720','373220',18.20),('305720','006400',14.60),('305720','005490',12.30);

-- KODEX 반도체
INSERT INTO etf_holdings VALUES
 ('091160','000660',22.40),('091160','005930',19.80);

-- TIGER 인터넷TOP10
INSERT INTO etf_holdings VALUES
 ('365000','035420',26.30),('365000','035720',23.80);

-- KODEX 바이오
INSERT INTO etf_holdings VALUES
 ('244580','068270',19.60),('244580','207940',17.40);

-- KODEX 은행
INSERT INTO etf_holdings VALUES
 ('091170','105560',24.10),('091170','055550',22.60);

-- PLUS K방산
INSERT INTO etf_holdings VALUES
 ('449450','012450',24.20),('449450','047810',16.90),('449450','079550',13.10),
 ('449450','000880',9.80);

-- SOL 조선TOP3플러스
INSERT INTO etf_holdings VALUES
 ('466920','329180',24.90);

-- 안전자산 ETF (채권형)
INSERT INTO etf_holdings VALUES
 ('439870','KRBOND03',82.00),('439870','KRBOND04',15.00),
 ('114260','KRBOND01',97.00),
 ('273130','KRBOND01',34.00),('273130','KRBOND02',31.00),('273130','KRBOND04',30.00);
