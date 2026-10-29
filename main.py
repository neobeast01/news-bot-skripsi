import sys
import os
import yaml
from loguru import logger

# --- PENGATURAN LOGGER (ABSOLUTE PATH) ---
# Dapatkan path folder tempat main.py berada
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Buat folder logs jika belum ada
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logger.remove()
logger.add(LOG_FILE, rotation="10 MB", encoding="utf-8")
if sys.stdout.isatty():
    logger.add(sys.stdout, colorize=True)
# ----------------------------------------

# (Lanjutan import di bawahnya)
from storage.db import (
    init_db, insert_article, count_by_category,
    job_start, job_finish,
)
from crawler.pipeline import crawl_by_categories
from nlp.run_on_db import process_pending
from nlp.run_extraction import process_extraction

def load_categories(path="config/sources.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["categories"]

def main():
    logger.info("=== MEMULAI PIPELINE CRAWLER (CEPAT) ===")
    init_db()
    job_id = job_start("cronjob_pipeline")
    
    try:
        # 1. Crawling
        categories = load_categories()
        articles = crawl_by_categories(categories)
        
        baru = 0
        for a in articles:
            if insert_article(a):
                baru += 1
        logger.info(f"Tersimpan {baru} artikel baru.")
        logger.info(f"Statistik: {count_by_category()}")

        # 2. NLP Processing
        process_pending(limit=500)

        # 3. Information Extraction
        process_extraction(limit=500)

        # Translasi DIHAPUS dari sini (dipindah ke report generator)

        job_finish(job_id, status="success", articles_found=len(articles), 
                   articles_processed=baru, records_created=baru)
        logger.info("=== PIPELINE CRAWLER SELESAI ===")

    except Exception as e:
        logger.exception(f"Pipeline gagal: {e}")
        job_finish(job_id, status="failed", error_message=str(e))
        raise

if __name__ == "__main__":
    main()