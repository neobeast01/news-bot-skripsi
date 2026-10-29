"""Cek hasil extraction dari MySQL."""
from storage.db import get_conn


def show_top(limit: int = 30):
    with get_conn() as c:
        cur = c.cursor(dictionary=True)
        cur.execute(
            """
            SELECT entity_type, entity_value, COUNT(*) AS n
              FROM extractions
             GROUP BY entity_type, entity_value
             ORDER BY n DESC
             LIMIT %s
            """,
            (limit,),
        )
        print(f"{'TYPE':15} | {'VALUE':60} | COUNT")
        print("-" * 90)
        for r in cur.fetchall():
            v = (r["entity_value"] or "")[:60]
            print(f"{r['entity_type']:15} | {v:60} | {r['n']}")


def show_per_type(limit_per_type: int = 10):
    """Tampilkan top entity per tipe."""
    types = ["cve", "malware", "threat_actor", "organization",
             "domain", "ipv4", "url", "email", "hash_md5", "hash_sha256"]
    with get_conn() as c:
        cur = c.cursor(dictionary=True)
        for t in types:
            cur.execute(
                """
                SELECT entity_value, COUNT(*) AS n
                  FROM extractions
                 WHERE entity_type = %s
                 GROUP BY entity_value
                 ORDER BY n DESC
                 LIMIT %s
                """,
                (t, limit_per_type),
            )
            rows = cur.fetchall()
            if not rows:
                continue
            print(f"\n=== {t.upper()} ({sum(r['n'] for r in rows)} total) ===")
            for r in rows:
                print(f"  {r['n']:3}x  {r['entity_value']}")


def show_stats():
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            "SELECT entity_type, COUNT(*) FROM extractions GROUP BY entity_type"
        )
        print("\n=== STATISTIK ENTITY ===")
        for t, n in cur.fetchall():
            print(f"  {t:15} : {n}")


if __name__ == "__main__":
    show_stats()
    show_top(30)
    show_per_type(10)