from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
STOPWORD_PATH = DATA_DIR / "stopwords_id.txt"
DOMAIN_PATH = DATA_DIR / "domain_terms.txt"


def _load_set(path):
    s = set()
    if not Path(path).exists():
        return s
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().lower()
            if not line or line.startswith("#"):
                continue
            s.add(line)
    return s


_STOPWORDS = _load_set(STOPWORD_PATH)
_DOMAIN = _load_set(DOMAIN_PATH)


def remove_stopwords(tokens: list[str]) -> list[str]:
    """
    Hapus token yang ada di stopword, KECUALI jika termasuk istilah domain.
    """
    return [
        t for t in tokens
        if (t not in _STOPWORDS) or (t in _DOMAIN)
    ]


def reload():
    global _STOPWORDS, _DOMAIN
    _STOPWORDS = _load_set(STOPWORD_PATH)
    _DOMAIN = _load_set(DOMAIN_PATH)