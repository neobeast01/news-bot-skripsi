import hashlib
import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "cti_reports"),
    "charset": "utf8mb4",
    "use_unicode": True,
    "autocommit": False,
}

SCHEMA_PATH = Path(__file__).parent / "schema_mysql.sql"


@contextmanager
def get_conn():
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


def _clean_sql(sql: str) -> str:
    """Buang komentar dan baris kosong."""
    lines = []
    for line in sql.splitlines():
        s = line.strip()
        if not s or s.startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines)


def init_db():
    """Buat database & tabel kalau belum ada."""
    # Connect tanpa database untuk CREATE DATABASE
    tmp_cfg = {
        "host": DB_CONFIG["host"],
        "port": DB_CONFIG["port"],
        "user": DB_CONFIG["user"],
        "password": DB_CONFIG["password"],
    }
    tmp = mysql.connector.connect(**tmp_cfg)
    cur = tmp.cursor()
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.close()
    tmp.close()

    # Buat tabel
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema_sql = _clean_sql(f.read())

    with get_conn() as conn:
        cur = conn.cursor()
        for stmt in schema_sql.split(";"):
            s = stmt.strip()
            if not s:
                continue
            cur.execute(s)
        conn.commit()
        cur.close()
    logger.info(f"MySQL siap: database={DB_CONFIG['database']}")


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _get_or_create_source(conn, name, base_url=None, rss_url=None, language="id"):
    cur = conn.cursor()
    cur.execute("SELECT id FROM sources WHERE name = %s", (name,))
    row = cur.fetchone()
    if row:
        cur.close()
        return row[0]
    cur.execute(
        "INSERT INTO sources (name, base_url, rss_url, language) VALUES (%s,%s,%s,%s)",
        (name, base_url, rss_url, language),
    )
    conn.commit()
    sid = cur.lastrowid
    cur.close()
    return sid


def insert_article(article: dict) -> bool:
    """Return True kalau baru, False kalau duplikat."""
    url = article["url"]
    url_hash = _hash_url(url)

    with get_conn() as conn:
        source_id = _get_or_create_source(
            conn,
            article.get("source", "unknown"),
            language=article.get("language", "id"),
        )
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO articles
                  (source_id, url, url_hash, title, author, published_at,
                   language, category, matched_keyword, content_raw, crawled_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    source_id,
                    url,
                    url_hash,
                    article.get("title"),
                    article.get("author"),
                    article.get("date"),
                    article.get("language", "id"),
                    article.get("category"),
                    article.get("keyword"),
                    article.get("content"),
                    article.get("crawled_at") or datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            return True
        except mysql.connector.IntegrityError:
            conn.rollback()
            return False
        finally:
            cur.close()


def count_by_category():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT category, COUNT(*) FROM articles GROUP BY category")
        result = {row[0] or "unknown": row[1] for row in cur.fetchall()}
        cur.close()
    return result


def get_unprocessed(limit: int = 100):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, title, content_raw FROM articles "
            "WHERE is_processed = 0 ORDER BY id LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()
        cur.close()
    return rows


def update_cleaned(article_id: int, cleaned_text: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE articles SET content_clean = %s, is_processed = 1 WHERE id = %s",
            (cleaned_text, article_id),
        )
        conn.commit()
        cur.close()


def job_start(job_type: str) -> str:
    job_id = str(uuid.uuid4())
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO job_logs (job_id, job_type, start_time, status) "
            "VALUES (%s, %s, NOW(), 'running')",
            (job_id, job_type),
        )
        conn.commit()
        cur.close()
    return job_id


def job_finish(job_id, status="success", articles_found=0,
               articles_processed=0, records_created=0, error_message=None):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE job_logs
               SET end_time = NOW(), status = %s,
                   articles_found = %s, articles_processed = %s,
                   records_created = %s, error_message = %s
             WHERE job_id = %s
            """,
            (status, articles_found, articles_processed,
             records_created, error_message, job_id),
        )
        conn.commit()
        cur.close()
        
# ============================================================
# Information Extraction
# ============================================================
def get_unextracted(limit: int = 200):
    """Ambil artikel yang sudah di-NLP tapi belum di-extract."""
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, title, url, content_raw, content_clean
              FROM articles
             WHERE is_processed = 1
               AND is_extracted = 0
             ORDER BY id
             LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        cur.close()
    return rows


def insert_extractions(article_id: int, entities: list[dict]) -> int:
    """Simpan list entity ke tabel extractions. Return jumlah tersimpan."""
    if not entities:
        return 0
    with get_conn() as conn:
        cur = conn.cursor()
        rows = [
            (
                article_id,
                e["entity_type"],
                e["entity_value"][:500],
                e.get("evidence", "")[:2000] or None,
                e.get("confidence", 1.0),
            )
            for e in entities
        ]
        cur.executemany(
            """
            INSERT INTO extractions
              (article_id, entity_type, entity_value, evidence, confidence)
            VALUES (%s, %s, %s, %s, %s)
            """,
            rows,
        )
        conn.commit()
        count = cur.rowcount
        cur.close()
    return count


def mark_extracted(article_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE articles SET is_extracted = 1 WHERE id = %s",
                    (article_id,))
        conn.commit()
        cur.close()


def count_extractions_by_type():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT entity_type, COUNT(*) FROM extractions GROUP BY entity_type"
        )
        result = {row[0]: row[1] for row in cur.fetchall()}
        cur.close()
    return result