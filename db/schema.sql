-- =========================================================
-- ETF 포트폴리오 최적화 시스템 DB 스키마 (MySQL / MariaDB)
-- Database: etf_db
-- =========================================================
SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS etf_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE etf_db;

-- ---------------------------------------------------------
-- 1) 국가 테이블
-- ---------------------------------------------------------
DROP TABLE IF EXISTS etf_holdings;
DROP TABLE IF EXISTS stock_themes;
DROP TABLE IF EXISTS stocks;
DROP TABLE IF EXISTS etfs;
DROP TABLE IF EXISTS themes;
DROP TABLE IF EXISTS sectors;
DROP TABLE IF EXISTS countries;

CREATE TABLE countries (
  country_code  VARCHAR(3)   PRIMARY KEY,          -- 예: KR, US
  country_name  VARCHAR(50)  NOT NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- 2) 섹터 테이블
-- ---------------------------------------------------------
CREATE TABLE sectors (
  sector_id    INT AUTO_INCREMENT PRIMARY KEY,
  sector_name  VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- 3) 테마 테이블
-- ---------------------------------------------------------
CREATE TABLE themes (
  theme_id    INT AUTO_INCREMENT PRIMARY KEY,
  theme_name  VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- 4) 주식 종목 테이블
-- ---------------------------------------------------------
CREATE TABLE stocks (
  stock_code    VARCHAR(12) PRIMARY KEY,            -- 예: 005930
  stock_name    VARCHAR(80) NOT NULL,
  sector_id     INT,
  country_code  VARCHAR(3),
  CONSTRAINT fk_stock_sector  FOREIGN KEY (sector_id)    REFERENCES sectors(sector_id),
  CONSTRAINT fk_stock_country FOREIGN KEY (country_code) REFERENCES countries(country_code),
  INDEX idx_stock_name (stock_name)
) ENGINE=InnoDB;

-- 주식-테마 매핑 (M:N)
CREATE TABLE stock_themes (
  stock_code VARCHAR(12) NOT NULL,
  theme_id   INT         NOT NULL,
  PRIMARY KEY (stock_code, theme_id),
  CONSTRAINT fk_st_stock FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE,
  CONSTRAINT fk_st_theme FOREIGN KEY (theme_id)   REFERENCES themes(theme_id)   ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- 5) ETF 기본 테이블
-- ---------------------------------------------------------
CREATE TABLE etfs (
  etf_code      VARCHAR(12) PRIMARY KEY,            -- 예: 069500
  etf_name      VARCHAR(100) NOT NULL,
  issuer        VARCHAR(50),
  asset_class   ENUM('RISK','SAFE') NOT NULL,       -- 위험자산 / 안전자산
  expense_ratio DECIMAL(6,4) DEFAULT 0,             -- 총보수(%)
  close_price   INT NOT NULL,                       -- 기준가(원) — 1주 단위 매매 계산용
  aum           BIGINT DEFAULT 0,                   -- 순자산(억원)
  country_code  VARCHAR(3),
  CONSTRAINT fk_etf_country FOREIGN KEY (country_code) REFERENCES countries(country_code),
  INDEX idx_etf_name (etf_name)
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- 6) ETF 구성종목 테이블
-- ---------------------------------------------------------
CREATE TABLE etf_holdings (
  etf_code   VARCHAR(12)  NOT NULL,
  stock_code VARCHAR(12)  NOT NULL,
  weight     DECIMAL(7,4) NOT NULL,                 -- 구성비중(%)
  PRIMARY KEY (etf_code, stock_code),
  CONSTRAINT fk_h_etf   FOREIGN KEY (etf_code)   REFERENCES etfs(etf_code)     ON DELETE CASCADE,
  CONSTRAINT fk_h_stock FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE,
  INDEX idx_h_stock (stock_code)
) ENGINE=InnoDB;
