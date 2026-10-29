"""Cek status translate artikel."""
from storage.db import get_conn

with get_conn() as c:
    cur = c.cursor()

    cur.execute("SELECT COUNT(*) FROM articles")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM articles WHERE language='en'")
    total_en = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM articles WHERE language='en' AND translated_at IS NULL")
    belum = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM articles WHERE language='en' AND translated_at IS NOT NULL")
    sudah = cur.fetchone()[0]

    cur.close()

print(f"Total artikel          : {total}")
print(f"Artikel EN             : {total_en}")
print(f"Sudah diterjemahkan    : {sudah}")
print(f"Belum diterjemahkan    : {belum}")