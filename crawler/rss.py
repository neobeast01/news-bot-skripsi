import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from loguru import logger

from crawler.base import BaseCrawler


class RSSCrawler(BaseCrawler):
    """Parser RSS generik. Ambil daftar item dari feed."""

    def __init__(self, rss_url: str, source_name: str):
        super().__init__(name=source_name, base_url="")
        self.rss_url = rss_url

    def fetch_items(self) -> list[dict]:
        """Return list of {source, url, title, date, summary}."""
        xml_text = self.fetch(self.rss_url)
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"[{self.name}] XML parse error: {e}")
            return []

        # Dukung Atom (<entry>) atau RSS (<item>)
        items = root.findall(".//item") or root.findall(
            ".//{http://www.w3.org/2005/Atom}entry"
        )

        results = []
        for item in items:
            title = self._get_text(item, ["title"]) or ""
            link = self._get_link(item)
            pub = self._get_text(item, ["pubDate", "published", "updated"]) or ""
            desc = self._get_text(item, ["description", "summary"]) or ""

            if not link:
                continue

            # Bersihkan HTML di summary
            desc = self._strip_html(desc)

            results.append({
                "source": self.name,
                "url": link.strip(),
                "title": title.strip(),
                "date": self._parse_date(pub),
                "summary": desc[:500],
            })
        return results

    # --------------------
    # Helpers
    # --------------------
    @staticmethod
    def _get_text(item, tags: list[str]) -> str:
        for tag in tags:
            el = item.find(tag)
            if el is not None and el.text:
                return el.text
            # namespace Atom
            el = item.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
            if el is not None and el.text:
                return el.text
        return ""

    @staticmethod
    def _get_link(item) -> str:
        # RSS 2.0: <link>URL</link>
        el = item.find("link")
        if el is not None:
            if el.text and el.text.strip():
                return el.text.strip()
            # Atom: <link href="..."/>
            href = el.get("href")
            if href:
                return href
        # Atom alternatif
        for link_el in item.findall("{http://www.w3.org/2005/Atom}link"):
            href = link_el.get("href")
            if href and link_el.get("rel", "alternate") in ("alternate", None):
                return href
        return ""

    @staticmethod
    def _strip_html(text: str) -> str:
        import re
        return re.sub(r"<[^>]+>", " ", text or "").strip()

    @staticmethod
    def _parse_date(pub: str) -> str | None:
        if not pub:
            return None
        try:
            return parsedate_to_datetime(pub).isoformat()
        except Exception:
            try:
                from datetime import datetime
                # Format ISO 8601 (Atom)
                return datetime.fromisoformat(pub.replace("Z", "+00:00")).isoformat()
            except Exception:
                return None