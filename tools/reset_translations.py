"""Reset hasil translate untuk re-run."""
from storage.db import get_conn

with get_conn() as c:
    cur = c.cursor()
    cur.execute("UPDATE articles SET content_id = NULL, translated_at = NULL WHERE language = 'en'")
    c.commit()
    print(f"Reset OK — {cur.rowcount} artikel EN di-mark untuk re-translate")
    cur.close()