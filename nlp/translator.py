"""Translator lokal EN → ID pakai Helsinki-NLP/opus-mt-en-id (offline)."""
from loguru import logger
from transformers import MarianMTModel, MarianTokenizer


MODEL_NAME = "Helsinki-NLP/opus-mt-en-id"

_model = None
_tokenizer = None


def _load_model():
    """Load model sekali saja (lazy loading)."""
    global _model, _tokenizer
    if _model is None:
        logger.info(f"Loading model {MODEL_NAME}... (pertama kali mungkin lambat)")
        _tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME)
        _model = MarianMTModel.from_pretrained(MODEL_NAME)
        logger.info("Model siap.")
    return _tokenizer, _model


def translate_to_id(text: str, max_len: int = 450) -> str:
    """Translate EN → ID pakai model lokal. max_len = max token per chunk."""
    if not text:
        return ""

    text = text.strip()
    if not text:
        return ""

    tokenizer, model = _load_model()

    # Pecah teks jadi kalimat-kalimat pendek (max 450 char)
    sentences = []
    for para in text.split("\n"):
        for sent in para.split(". "):
            sent = sent.strip()
            if sent:
                sentences.append(sent + ".")

    # Gabungkan kalimat jadi chunk ~400 char
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) < max_len:
            current += s + " "
        else:
            if current:
                chunks.append(current.strip())
            current = s + " "
    if current:
        chunks.append(current.strip())

    if not chunks:
        return ""

    # Batch translate (efisien, satu forward pass per batch)
    try:
        inputs = tokenizer(chunks, return_tensors="pt", padding=True,
                          truncation=True, max_length=512)
        outputs = model.generate(**inputs, max_length=512, num_beams=2)
        translated = [
            tokenizer.decode(o, skip_special_tokens=True)
            for o in outputs
        ]
        return " ".join(translated)
    except Exception as e:
        logger.error(f"Translate gagal: {e}")
        return text