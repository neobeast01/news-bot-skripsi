-- CTI Reports - MySQL Schema

DROP TABLE IF EXISTS delivery_logs;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS keywords;
DROP TABLE IF EXISTS extractions;
DROP TABLE IF EXISTS articles;
DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS job_logs;

CREATE TABLE sources (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL UNIQUE,
    base_url      VARCHAR(500),
    rss_url       VARCHAR(500),
    language      VARCHAR(5) DEFAULT 'id',
    is_active     TINYINT(1) DEFAULT 1,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE articles (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    source_id     INT,
    url           VARCHAR(1000) NOT NULL,
    url_hash      CHAR(64) NOT NULL UNIQUE,
    title         TEXT,
    author        VARCHAR(255),
    published_at  DATETIME,
    language      VARCHAR(5),
    category      VARCHAR(100),
    matched_keyword VARCHAR(200),
    content_raw   LONGTEXT,
    content_clean LONGTEXT,
    content_id    LONGTEXT,          -- <-- TAMBAHKAN INI
    translated_at DATETIME,          -- <-- TAMBAHKAN INI
    is_processed  TINYINT(1) DEFAULT 0,
    is_extracted  TINYINT(1) DEFAULT 0,
    crawled_at    DATETIME NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_processed (is_processed),
    INDEX idx_extracted (is_extracted),
    INDEX idx_published (published_at),
    INDEX idx_language (language),
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE extractions (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    article_id    BIGINT NOT NULL,
    entity_type   VARCHAR(50) NOT NULL,
    entity_value  VARCHAR(500) NOT NULL,
    evidence      TEXT,
    confidence    FLOAT DEFAULT 1.0,
    extracted_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_article (article_id),
    INDEX idx_type (entity_type),
    INDEX idx_value (entity_value(100)),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE keywords (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    article_id    BIGINT NOT NULL,
    keyword       VARCHAR(200) NOT NULL,
    frequency     INT DEFAULT 1,
    score         FLOAT DEFAULT 0.0,
    INDEX idx_article (article_id),
    INDEX idx_keyword (keyword(100)),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE reports (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    report_code   VARCHAR(100) NOT NULL UNIQUE,
    period_start  DATE,
    period_end    DATE,
    title         VARCHAR(500),
    total_articles INT DEFAULT 0,
    file_path     VARCHAR(500),
    generated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_period (period_start, period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE delivery_logs (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    report_id     BIGINT,
    recipient     VARCHAR(100),
    status        VARCHAR(50) DEFAULT 'pending',
    message_id    VARCHAR(200),
    error_message TEXT,
    sent_at       DATETIME,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_report (report_id),
    INDEX idx_status (status),
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE job_logs (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_id        VARCHAR(100) NOT NULL,
    job_type      VARCHAR(50) NOT NULL,
    start_time    DATETIME NOT NULL,
    end_time      DATETIME,
    status        VARCHAR(50) DEFAULT 'running',
    articles_found INT DEFAULT 0,
    articles_processed INT DEFAULT 0,
    records_created INT DEFAULT 0,
    error_message TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_job_id (job_id),
    INDEX idx_type (job_type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;