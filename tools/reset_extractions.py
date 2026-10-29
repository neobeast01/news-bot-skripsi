"""Reset hasil extraction untuk re-run."""
from storage.db import get_conn

with get_conn() as c:
    cur = c.cursor()
    cur.execute("DELETE FROM extractions")
    cur.execute("UPDATE articles SET is_extracted = 0")
    c.commit()
    print(f"Reset OK — {cur.rowcount} artikel di-mark untuk re-extract")
    cur.close()