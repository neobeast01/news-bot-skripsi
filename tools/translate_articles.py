"""Batch translate artikel EN ke ID, simpan ke kolom content_id."""
import time
from loguru import logger
from storage.db import get_conn
from nlp.translator import translate_to_id


DELAY_BETWEEN_ARTICLES = 1.0  # detik


def get_untranslated(limit: int = 100):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, title, content_raw
              FROM articles
             WHERE language = 'en'
               AND translated_at IS NULL
             ORDER BY id
             LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        cur.close()
    return rows


def save_translation(article_id: int, content_id: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE articles SET content_id = %s, translated_at = NOW() WHERE id = %s",
            (content_id, article_id),
        )
        conn.commit()
        cur.close()


def main(limit: int = 100):
    rows = get_untranslated(limit)
    if not rows:
        logger.info("Tidak ada artikel pending untuk translate")
        return

    logger.info(f"Translate {len(rows)} artikel EN → ID...")
    logger.info(f"Estimasi waktu: {len(rows) * 3 // 60} menit")

    sukses = 0
    for i, row in enumerate(rows, 1):
        logger.info(f"  [{i}/{len(rows)}] {row['title'][:60]}")
        try:
            translated = translate_to_id(row["content_raw"] or "")
            if translated and translated != (row["content_raw"] or "")[:len(translated)]:
                save_translation(row["id"], translated)
                sukses += 1
            else:
                logger.warning(f"  Hasil translate mencurigakan, skip simpan")
        except Exception as e:
            logger.error(f"  Gagal id={row['id']}: {e}")

        time.sleep(DELAY_BETWEEN_ARTICLES)

    logger.info(f"Selesai. {sukses}/{len(rows)} artikel berhasil diterjemahkan")


if __name__ == "__main__":
    main(limit=40)