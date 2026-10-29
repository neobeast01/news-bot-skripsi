from loguru import logger

from storage.db import (
    get_unextracted,
    insert_extractions,
    mark_extracted,
    count_extractions_by_type,
)
from nlp.extractor import extract_all


def process_extraction(limit: int = 200) -> int:
    """Jalankan extraction pada artikel yang belum diproses."""
    rows = get_unextracted(limit)
    if not rows:
        logger.info("Tidak ada artikel pending untuk extraction")
        return 0

    logger.info(f"Memproses extraction untuk {len(rows)} artikel...")

    total_entities = 0
    processed = 0
    for row in rows:
        try:
            text = f"{row['title'] or ''}\n{row['content_raw'] or ''}"
            entities = extract_all(text, source_url=row.get("url"))

            if entities:
                n = insert_extractions(row["id"], entities)
                total_entities += n

            mark_extracted(row["id"])
            processed += 1
        except Exception as e:
            logger.error(f"Gagal extraction id={row['id']}: {e}")

    logger.info(
        f"Selesai. {processed}/{len(rows)} artikel di-extract, "
        f"{total_entities} entity tersimpan"
    )
    logger.info(f"Statistik entity: {count_extractions_by_type()}")
    return processed


if __name__ == "__main__":
    process_extraction(limit=500)