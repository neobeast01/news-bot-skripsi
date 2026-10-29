from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

_factory = StemmerFactory()
_stemmer = _factory.create_stemmer()


def stem_tokens(tokens: list[str]) -> list[str]:
    """Stemming satu batch token."""
    if not tokens:
        return []
    # Sastrawi lebih efisien kalau diberi kalimat panjang
    joined = " ".join(tokens)
    stemmed = _stemmer.stem(joined)
    return stemmed.split()