import re
import unicodedata

URL_RE     = re.compile(r"https?://\S+|www\.\S+")
EMAIL_RE   = re.compile(r"\S+@\S+\.\S+")
HTML_RE    = re.compile(r"<[^>]+>")
MENTION_RE = re.compile(r"@\w+")
HASHTAG_RE = re.compile(r"#\w+")
NON_WORD_RE = re.compile(r"[^a-z0-9\s\-]")
NUMBER_RE  = re.compile(r"\b\d+\b")
MULTISPACE_RE = re.compile(r"\s+")


def clean_text(text: str, remove_numbers: bool = True) -> str:
    """Bersihkan teks mentah jadi huruf kecil + spasi saja."""
    if not text:
        return ""

    # Normalisasi unicode (mis. "ﬁ" -> "fi", emoji kombinasi, dll)
    text = unicodedata.normalize("NFKC", text)

    # Lowercase
    text = text.lower()

    # Buang URL, email, HTML, mention, hashtag
    text = URL_RE.sub(" ", text)
    text = EMAIL_RE.sub(" ", text)
    text = HTML_RE.sub(" ", text)
    text = MENTION_RE.sub(" ", text)
    text = HASHTAG_RE.sub(" ", text)

    # Buang karakter non-alfanumerik (kecuali spasi dan tanda hubung)
    text = NON_WORD_RE.sub(" ", text)

    # Buang angka
    if remove_numbers:
        text = NUMBER_RE.sub(" ", text)

    # Rapikan spasi ganda
    text = MULTISPACE_RE.sub(" ", text).strip()
    return text