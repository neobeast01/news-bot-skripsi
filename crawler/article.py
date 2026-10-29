import trafilatura
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    source: str
    url: str
    title: Optional[str]
    author: Optional[str]
    date: Optional[str]
    content: Optional[str]
    crawled_at: str

    def to_dict(self):
        return asdict(self)


def extract_article(html: str, url: str, source: str) -> Article:
    extracted = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
        output_format="json",
        with_metadata=True,
    )

    if not extracted:
        return Article(source, url, None, None, None, None,
                       datetime.utcnow().isoformat())

    import json
    data = json.loads(extracted)

    return Article(
        source=source,
        url=url,
        title=data.get("title"),
        author=data.get("author"),
        date=data.get("date"),
        content=data.get("text"),
        crawled_at=datetime.utcnow().isoformat(),
    )