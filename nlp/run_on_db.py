from loguru import logger

from storage.db import get_unprocessed, update_cleaned
from nlp.pipeline import process_article


def process_pending(limit: int = 100) -> int:
    rows = get_unprocessed(limit)
    if not rows:
        logger.info("Tidak ada artikel pending untuk diproses NLP")
        return 0

    logger.info(f"Memproses NLP untuk {len(rows)} artikel...")
    ok = 0
    for row in rows:
        try:
            cleaned = process_article(
                title=row["title"] or "",
                content=row["content_raw"] or "",
            )
            update_cleaned(row["id"], cleaned["content_clean"])
            ok += 1
        except Exception as e:
            logger.error(f"Gagal NLP id={row['id']}: {e}")
    logger.info(f"Selesai. {ok}/{len(rows)} artikel di-NLP.")
    return ok


if __name__ == "__main__":
    process_pending(limit=200)