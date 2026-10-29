from loguru import logger
from crawler.base import BaseCrawler
from crawler.article import extract_article


class GenericCrawler(BaseCrawler):
    def __init__(self, cfg: dict):
        super().__init__(cfg["name"], cfg["base_url"])
        self.list_url = cfg["list_url"]
        self.selector = cfg["article_selector"]
        self.max_articles = cfg.get("max_articles", 20)

    def run(self) -> list:
        html = self.fetch(self.list_url)
        links = self.parse_list(html, self.selector)[: self.max_articles]
        logger.info(f"[{self.name}] ditemukan {len(links)} link")

        articles = []
        for link in links:
            try:
                art_html = self.fetch(link)
                art = extract_article(art_html, link, self.name)
                if art.content and len(art.content) > 200:
                    articles.append(art)
                else:
                    logger.warning(f"[{self.name}] konten pendek / kosong: {link}")
            except Exception as e:
                logger.error(f"[{self.name}] gagal {link}: {e}")
        return articles