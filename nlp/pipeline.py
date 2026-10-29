import re
from nlp.cleaner import clean_text
from nlp.normalizer import normalize_tokens
from nlp.stopword import remove_stopwords
from nlp.stemmer import stem_tokens

# Token: minimal 2 huruf, hanya a-z dan tanda hubung
TOKEN_RE = re.compile(r"\b[a-z][a-z\-]+\b")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def process_text(text: str, do_stem: bool = True) -> str:
    if not text:
        return ""
    cleaned = clean_text(text)
    tokens = tokenize(cleaned)
    tokens = normalize_tokens(tokens)
    tokens = remove_stopwords(tokens)
    tokens = [t for t in tokens if len(t) > 2]   # buang token 1-2 huruf
    if do_stem:
        tokens = stem_tokens(tokens)
    return " ".join(tokens)


def process_article(title: str, content: str) -> dict:
    return {
        "title_clean": process_text(title or "", do_stem=False),  # <-- ganti
        "content_clean": process_text(content or "", do_stem=False),  # <-- ganti
    }