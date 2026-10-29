import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}


class BaseCrawler:
    def __init__(self, name: str, base_url: str, timeout: int = 15):
        self.name = name
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def fetch(self, url: str) -> str:
        logger.info(f"[{self.name}] GET {url}")
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def parse_list(self, html: str, selector: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        links = []
        for a in soup.select(selector):
            href = a.get("href")
            if not href:
                continue
            if href.startswith("/"):
                href = self.base_url + href
            if href.startswith("http"):
                links.append(href)
        # dedupe, preserve order
        return list(dict.fromkeys(links))