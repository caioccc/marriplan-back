from __future__ import annotations

import logging
import random
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Sequence
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ScrapedProduct:
    title: str
    description: str
    price: str
    image_url: str
    product_url: str
    category: str
    store: str

    def as_dict(self) -> dict[str, str]:
        return {
            'title': self.title,
            'description': self.description,
            'price': self.price,
            'image_url': self.image_url,
            'product_url': self.product_url,
            'category': self.category,
            'store': self.store,
        }


class BaseMarketplaceScraper(ABC):
    marketplace_key = ''
    marketplace_label = ''
    base_url = ''
    default_max_results = 12
    retry_count = 2
    delay_range = (0.8, 1.8)

    def __init__(self, timeout: int = 25, max_results: int = 12, session: requests.Session | None = None):
        self.timeout = timeout
        self.max_results = max_results
        self.session = session or requests.Session()
        self.session.headers.update(self._static_headers())

    def search_products(self, term: str, max_results: int | None = None) -> list[dict]:
        term = self._clean_text(term)
        if not term:
            return []

        limit = max_results or self.max_results or self.default_max_results
        for attempt in range(1, self.retry_count + 2):
            try:
                return self._search_once(term, limit)
            except Exception as exc:
                logger.warning(
                    '%s falhou ao pesquisar "%s" na tentativa %s/%s: %s',
                    self.marketplace_label,
                    term,
                    attempt,
                    self.retry_count + 1,
                    exc,
                )
                if attempt >= self.retry_count + 1:
                    raise
                self._sleep_random(0.8, 1.4)

        return []

    def _search_once(self, term: str, limit: int) -> list[dict]:
        search_url = self.build_search_url(term)
        logger.info('Consultando %s com termo "%s"', self.marketplace_label, term)
        html = self._fetch_html(search_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        results: list[dict] = []
        for card in self.extract_cards(soup):
            if len(results) >= limit:
                break

            product = self.parse_card(card, fallback_term=term)
            if not product or not product.title or not product.product_url:
                continue

            results.append(product.as_dict())

        return results

    def _fetch_html(self, url: str) -> str:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()

        if self._looks_blocked(response.text):
            raise RuntimeError(f'{self.marketplace_label} bloqueou a requisicao.')

        self._sleep_random()
        return response.text

    def _static_headers(self) -> dict[str, str]:
        return {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        }

    def _looks_blocked(self, html: str) -> bool:
        lowered = (html or '').lower()
        signatures = (
            'captcha',
            'robot check',
            'access denied',
            'verify you are human',
            'unusual traffic',
            'powered and protected by',
            'chlgeid',
        )
        return any(signature in lowered for signature in signatures)

    def _sleep_random(self, minimum: float | None = None, maximum: float | None = None) -> None:
        low, high = minimum or self.delay_range[0], maximum or self.delay_range[1]
        time.sleep(random.uniform(low, high))

    @abstractmethod
    def build_search_url(self, term: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def extract_cards(self, soup: BeautifulSoup):
        raise NotImplementedError

    @abstractmethod
    def parse_card(self, card, fallback_term: str) -> ScrapedProduct | None:
        raise NotImplementedError

    def _resolve_url(self, href: str | None) -> str:
        if not href:
            return ''
        return urljoin(self.base_url, href)

    def _clean_text(self, value: str | None) -> str:
        return re.sub(r'\s+', ' ', value or '').strip()

    def _text_from(self, node) -> str:
        return self._clean_text(node.get_text(' ', strip=True) if node else '')

    def _first_text(self, nodes: Iterable) -> str:
        for node in nodes:
            text = self._text_from(node)
            if text:
                return text
        return ''

    def _guess_category(self, title: str, description: str) -> str:
        text = f'{title} {description}'.lower()
        keyword_map: Sequence[tuple[str, Sequence[str]]] = (
            ('cozinha', ('air fryer', 'panela', 'cafeteira', 'liquidificador', 'batedeira', 'fogao', 'microondas', 'cozinha', 'utensilios')),
            ('eletrodomesticos', ('geladeira', 'lava e seca', 'maquina de lavar', 'secadora', 'ar condicionado', 'ventilador', 'aspirador', 'bebedouro', 'frigobar', 'purificador')),
            ('moveis', ('sofa', 'rack', 'painel', 'mesa', 'cadeira', 'cama', 'guarda roupa', 'comoda', 'aparador', 'poltrona', 'sapateira')),
            ('quarto', ('cama', 'colcha', 'edredom', 'travesseiro', 'protetor de colchao', 'manta', 'abajur', 'cortina', 'enxoval')),
            ('banheiro', ('toalha', 'tapete banheiro', 'lixeira', 'espelho banheiro', 'toalheiro', 'porta papel', 'sabonete', 'chuveiro', 'ducha')),
            ('decoracao', ('quadro', 'vaso', 'espelho decorativo', 'luminaria', 'abajur', 'vela', 'aromatizador', 'porta retrato', 'escultura', 'bandeja')),
            ('tecnologia', ('smart tv', 'notebook', 'tablet', 'smartphone', 'smartwatch', 'fone bluetooth', 'caixa de som', 'roteador', 'monitor', 'teclado', 'mouse')),
            ('lavanderia', ('ferro', 'tabua de passar', 'varal', 'cesto', 'sabao', 'amaciante', 'vaporizador', 'lavadora')),
            ('lua_de_mel', ('mala', 'mochila', 'frasqueira', 'necessaire', 'travesseiro de pescoco', 'cadeado', 'adaptador', 'power bank', 'camera instantanea')),
        )

        for category, keywords in keyword_map:
            if any(keyword in text for keyword in keywords):
                return category

        return 'outros'
