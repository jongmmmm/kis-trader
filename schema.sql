-- ============================================
-- KIS Trader Database Schema
-- SQLite3
-- Generated: 2026-03-15
-- ============================================

-- 사용자 테이블
CREATE TABLE users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        VARCHAR(20)  NOT NULL UNIQUE,       -- 로그인 ID
    password_hash   VARCHAR(256) NOT NULL,              -- 비밀번호 해시
    name            VARCHAR(50)  DEFAULT '',            -- 이름
    phone           VARCHAR(11)  DEFAULT '',            -- 전화번호
    email           VARCHAR(120) DEFAULT '',            -- 이메일
    birth_date      VARCHAR(10)  DEFAULT '',            -- 생년월일
    remember_token  VARCHAR(256) DEFAULT '',            -- 자동 로그인 토큰
    login_method    VARCHAR(20)  DEFAULT 'password',    -- password | webauthn
    webauthn_credentials JSON    DEFAULT '[]',          -- WebAuthn 인증 정보
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP
);

-- 전략 테이블
CREATE TABLE strategies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            VARCHAR(100) NOT NULL,              -- 전략 이름
    stock_code      VARCHAR(10)  NOT NULL,              -- 종목 코드 (005930, AAPL 등)
    stock_name      VARCHAR(50)  DEFAULT '',            -- 종목명
    exchange        VARCHAR(10)  DEFAULT '',            -- 거래소 (빈값=국내, NAS/NYS/AMS/HKS/TSE=해외)
    strategy_type   VARCHAR(20)  NOT NULL,              -- ma | rsi_macd | condition | ml
    params          JSON         DEFAULT '{}',          -- 전략 파라미터 (이평선 기간, RSI 임계값 등)
    is_active       BOOLEAN      DEFAULT 1,             -- 활성 여부
    mode            VARCHAR(10)  DEFAULT 'paper',       -- paper(모의) | real(실전)
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP
);

-- 주문 내역 테이블
CREATE TABLE orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id     INTEGER,                            -- 전략 FK (NULL=수동 주문)
    stock_code      VARCHAR(10)  NOT NULL,              -- 종목 코드
    order_type      VARCHAR(4)   NOT NULL,              -- buy | sell
    price           FLOAT        DEFAULT 0,             -- 주문 가격
    quantity        INTEGER      DEFAULT 0,             -- 주문 수량
    status          VARCHAR(20)  DEFAULT 'pending',     -- pending | submitted | filled | cancelled
    "trigger"       VARCHAR(20)  DEFAULT 'auto',        -- auto | auction_manual
    mode            VARCHAR(10)  DEFAULT 'paper',       -- paper | real
    kis_order_no    VARCHAR(50)  DEFAULT '',             -- KIS 주문번호
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);

-- 동시호가 AI 알림 테이블
CREATE TABLE auction_alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id     INTEGER,                            -- 전략 FK
    stock_code      VARCHAR(10)  NOT NULL,              -- 종목 코드
    stock_name      VARCHAR(50)  DEFAULT '',            -- 종목명
    suggested_action VARCHAR(4),                        -- buy | sell | hold
    suggested_price FLOAT        DEFAULT 0,             -- AI 제안 가격
    suggested_qty   INTEGER      DEFAULT 0,             -- AI 제안 수량
    ai_confidence   INTEGER      DEFAULT 0,             -- AI 신뢰도 (0~100)
    ai_score        FLOAT        DEFAULT 0,             -- AI 점수 (-100~100)
    ai_summary      TEXT         DEFAULT '',            -- AI 종합 요약
    ai_factors      JSON         DEFAULT '[]',          -- 팩터별 분석 상세
    user_decision   VARCHAR(4),                         -- buy | sell | pass | NULL
    decided_at      DATETIME,                           -- 사용자 결정 시각
    expires_at      DATETIME     NOT NULL,              -- 알림 만료 시각
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);

-- 포트폴리오 스냅샷 테이블
CREATE TABLE portfolio_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mode            VARCHAR(10),                        -- paper | real
    stock_code      VARCHAR(10),                        -- 종목 코드
    quantity        INTEGER      DEFAULT 0,             -- 보유 수량
    avg_price       FLOAT        DEFAULT 0,             -- 평균 매입가
    current_price   FLOAT        DEFAULT 0,             -- 현재가
    snapped_at      DATETIME     DEFAULT CURRENT_TIMESTAMP
);

-- KIS API 토큰 캐시 테이블
CREATE TABLE kis_tokens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mode            VARCHAR(10)  UNIQUE,                -- paper | real
    access_token    TEXT         DEFAULT '',             -- OAuth2 액세스 토큰
    expires_at      DATETIME,                           -- 토큰 만료 시각
    updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP
);
