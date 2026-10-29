"""Cek berita baru yang masuk hari ini."""
from datetime import datetime, timedelta
from storage.db import get_conn

with get_conn() as conn:
    cur = conn.cursor(dictionary=True)

    # Artikel 24 jam terakhir
    cur.execute("""
        SELECT id, title, published_at, category
          FROM articles
         WHERE published_at >= NOW() - INTERVAL 24 HOUR
         ORDER BY published_at DESC
    """)
    rows = cur.fetchall()

print(f"📰 Artikel dalam 24 jam terakhir: {len(rows)}")
for r in rows:
    tgl = r["published_at"].strftime("%H:%M %d/%m")
    print(f"  [{tgl}] [{r['category']:15}] {r['title'][:70]}")