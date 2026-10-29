from pathlib import Path

SLANG_PATH = Path(__file__).parent / "data" / "slang_dict.txt"


def load_slang_dict(path=SLANG_PATH) -> dict:
    d = {}
    if not Path(path).exists():
        return d
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k.strip().lower()] = v.strip().lower()
    return d


_SLANG = load_slang_dict()


def normalize_tokens(tokens: list[str]) -> list[str]:
    """Ganti setiap token slang dengan bentuk baku."""
    return [_SLANG.get(t, t) for t in tokens]


def reload():
    """Reload kamus dari file (untuk runtime update)."""
    global _SLANG
    _SLANG = load_slang_dict()