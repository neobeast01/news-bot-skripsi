import re
from pathlib import Path
from loguru import logger

DICT_DIR = Path(__file__).parent / "data" / "cyber_dict"


# ============================================================
# Regex patterns untuk IOC teknis
# ============================================================
REGEX_PATTERNS = {
    "cve": re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "url": re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE),
    "email": re.compile(r"\b[\w.\-+]+@[\w.\-]+\.\w+\b"),
    "hash_md5": re.compile(r"\b[a-f0-9]{32}\b", re.IGNORECASE),
    "hash_sha1": re.compile(r"\b[a-f0-9]{40}\b", re.IGNORECASE),
    "hash_sha256": re.compile(r"\b[a-f0-9]{64}\b", re.IGNORECASE),
    "domain": re.compile(
        r"\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+"
        r"(?:com|net|org|io|gov|edu|co|id|ru|cn|uk|de|info|biz|xyz|top|onion)\b",
        re.IGNORECASE,
    ),
}

# Filter: domain yang tidak relevan
DOMAIN_BLACKLIST = {
    "example.com", "example.org", "test.com", "localhost",
}


# ============================================================
# Load dictionary
# ============================================================
def _load_dict(filename: str) -> set[str]:
    path = DICT_DIR / filename
    if not path.exists():
        logger.warning(f"Dictionary tidak ditemukan: {path}")
        return set()
    with open(path, encoding="utf-8") as f:
        return {line.strip().lower() for line in f
                if line.strip() and not line.startswith("#")}


MALWARE_DICT = _load_dict("malware.txt")
THREAT_ACTOR_DICT = _load_dict("threat_actors.txt")
ORGANIZATION_DICT = _load_dict("organizations.txt")


# ============================================================
# Evidence: ambil kalimat sekitar entity
# ============================================================
def _get_evidence(text: str, entity: str, window: int = 120) -> str:
    """Ambil potongan teks sekitar entity sebagai evidence."""
    idx = text.lower().find(entity.lower())
    if idx < 0:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(entity) + window)
    snippet = text[start:end].strip()
    # Rapikan spasi
    return re.sub(r"\s+", " ", snippet)


# ============================================================
# Ekstraksi regex (IOC teknis)
# ============================================================
def extract_regex(text: str, source_url: str = None) -> list[dict]:
    """Ekstrak IOC regex. Kalau source_url diberikan, filter self-reference."""
    results = []
    source_domain = None
    if source_url:
        m = re.search(r"https?://([^/]+)", source_url)
        if m:
            source_domain = m.group(1).lower().lstrip("www.")

    for etype, pattern in REGEX_PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group(0).strip()

            if etype == "ipv4":
                octets = value.split(".")
                if any(int(o) > 255 for o in octets):
                    continue

            if etype == "domain":
                if value.lower() in DOMAIN_BLACKLIST:
                    continue
                # Skip domain sumber artikelnya sendiri
                if source_domain and value.lower().endswith(source_domain):
                    continue

            results.append({
                "entity_type": etype,
                "entity_value": value,
                "evidence": _get_evidence(text, value),
                "confidence": 1.0,
            })

    seen = set()
    unique = []
    for r in results:
        key = (r["entity_type"], r["entity_value"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


# ============================================================
# Ekstraksi dictionary (malware, threat actor, organization)
# ============================================================
def extract_dictionary(text: str, dictionary: set[str], entity_type: str) -> list[dict]:
    """Cari nama entity dari dictionary dalam teks (case-insensitive, word-boundary)."""
    results = []
    lower = text.lower()
    for name in dictionary:
        # Pakai word boundary supaya "hive" tidak match "archive"
        pattern = r"\b" + re.escape(name) + r"\b"
        if re.search(pattern, lower):
            # Ambil versi asli dari teks (untuk evidence capitalization)
            m = re.search(pattern, lower)
            if m:
                orig = text[m.start():m.end()]
                results.append({
                    "entity_type": entity_type,
                    "entity_value": orig,  # pertahankan kapitalisasi asli
                    "evidence": _get_evidence(text, orig),
                    "confidence": 0.9,
                })
    return results


# ============================================================
# Pipeline utama: ekstrak semua dari teks
# ============================================================
def extract_all(text: str, source_url: str = None) -> list[dict]:
    """Ekstrak semua entity dari teks."""
    if not text:
        return []

    results = []
    results.extend(extract_regex(text, source_url=source_url))
    results.extend(extract_dictionary(text, MALWARE_DICT, "malware"))
    results.extend(extract_dictionary(text, THREAT_ACTOR_DICT, "threat_actor"))
    results.extend(extract_dictionary(text, ORGANIZATION_DICT, "organization"))

    seen = set()
    unique = []
    for r in results:
        key = (r["entity_type"], r["entity_value"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


# ============================================================
# CLI test cepat
# ============================================================
if __name__ == "__main__":
    sample = """
    A critical CVE-2024-12345 vulnerability in SonicWall SMA 1000 was
    exploited by APT28 and the LockBit ransomware group. The attacker
    used IP 192.168.1.10 and domain evil.example.org. Microsoft released
    a patch. Hash: a3f5c8e9b1d2f4a6c8e0d2f4a6c8e0d2 (MD5).
    """
    for r in extract_all(sample):
        print(f"{r['entity_type']:15} | {r['entity_value']}")