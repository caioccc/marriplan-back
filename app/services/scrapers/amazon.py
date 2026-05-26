from __future__ import annotations

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .base import BaseMarketplaceScraper, ScrapedProduct


class AmazonScraper(BaseMarketplaceScraper):
    marketplace_key = 'amazon'
    marketplace_label = 'Amazon Brasil'
    base_url = 'https://www.amazon.com.br'

    def build_search_url(self, term: str) -> str:
        return f'{self.base_url}/s?k={quote_plus(term)}'

    def extract_cards(self, soup: BeautifulSoup):
        return soup.select('div.s-result-item[data-component-type="s-search-result"]')

    def parse_card(self, card, fallback_term: str) -> ScrapedProduct | None:
        title = self._first_text([
            card.select_one('h2 a span'),
            card.select_one('h2 span'),
            card.select_one('h2'),
        ])

        link_node = (
            card.select_one('h2 a[href]')
            or card.select_one('a.a-link-normal[href*="/dp/"]')
            or card.select_one('a.a-link-normal[href*="/gp/product/"]')
            or card.select_one('a.a-link-normal[href*="/sspa/click"]')
        )
        product_url = self._resolve_url(link_node.get('href') if link_node else None)
        if not title or not product_url:
            return None

        image_node = card.select_one('img.s-image')
        image_url = ''
        if image_node:
            image_url = (
                image_node.get('src')
                or image_node.get('data-src')
                or image_node.get('data-lazy-src')
                or image_node.get('data-old-hires')
                or ''
            )

        price = self._first_text([
            card.select_one('span.a-price span.a-offscreen'),
            card.select_one('span.a-offscreen'),
        ])
        if not price:
            whole = self._first_text([card.select_one('span.a-price-whole')])
            fraction = self._first_text([card.select_one('span.a-price-fraction')])
            if whole:
                price = f'R$ {whole},{fraction or "00"}'
        if not price:
            price = 'Preco indisponivel'

        description = self._first_text([
            card.select_one('span.a-size-base-plus.a-color-base.a-text-normal'),
            card.select_one('span.a-size-base.a-color-base'),
            card.select_one('div.a-row.a-size-base.a-color-base'),
        ])
        if not description:
            description = title

        category = self._guess_category(title, description or fallback_term)

        return ScrapedProduct(
            title=title,
            description=description,
            price=price,
            image_url=image_url,
            product_url=product_url,
            category=category,
            store=self.marketplace_label,
        )

