from __future__ import annotations

import logging
import random
import time
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from app.models import ProductCatalog
from app.services.scrapers.amazon import AmazonScraper
from app.utils import parse_money_value


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Popula o ProductCatalog com itens essenciais a partir de um arquivo .txt e do scraper da Amazon.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input-file',
            default=str(Path(settings.BASE_DIR) / 'lista_basica_presentes.txt'),
            help='Arquivo .txt com um item essencial por linha.',
        )
        parser.add_argument(
            '--limit-per-item',
            type=int,
            default=1,
            help='Quantidade máxima de resultados solicitados ao scraper por item.',
        )
        parser.add_argument(
            '--delay-min',
            type=float,
            default=1.0,
            help='Pausa mínima entre requisições.',
        )
        parser.add_argument(
            '--delay-max',
            type=float,
            default=2.5,
            help='Pausa máxima entre requisições.',
        )

    def handle(self, *args, **options):
        input_path = Path(options['input_file']).expanduser()
        if not input_path.exists():
            raise CommandError(f'Arquivo de entrada não encontrado: {input_path}')

        terms = self._load_terms(input_path)
        if not terms:
            raise CommandError('Nenhum item essencial foi encontrado no arquivo de entrada.')

        limit_per_item = max(1, options['limit_per_item'])
        delay_min = max(0.0, options['delay_min'])
        delay_max = max(delay_min, options['delay_max'])
        scraper = AmazonScraper(max_results=limit_per_item)

        stats = {'items': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

        self.stdout.write(self.style.SUCCESS(f'Populando catálogo básico com {len(terms)} item(ns).'))

        for term in terms:
            stats['items'] += 1
            self.stdout.write(f'Buscando "{term}" na Amazon...')
            try:
                results = scraper.search_products(term, max_results=limit_per_item)
            except Exception as exc:
                stats['errors'] += 1
                logger.exception('Falha ao buscar termo essencial "%s"', term)
                self.stdout.write(self.style.WARNING(f'Falha ao consultar "{term}": {exc}'))
                self._sleep_between_requests(delay_min, delay_max)
                continue

            if not results:
                stats['skipped'] += 1
                self.stdout.write(self.style.WARNING(f'Nenhum produto encontrado para "{term}".'))
                self._sleep_between_requests(delay_min, delay_max)
                continue

            product, created = self._upsert_catalog_product(results[0], term)
            if created:
                stats['created'] += 1
                self.stdout.write(self.style.SUCCESS(f'Criado: {product.title}'))
            else:
                stats['updated'] += 1
                self.stdout.write(self.style.SUCCESS(f'Atualizado: {product.title}'))

            self._sleep_between_requests(delay_min, delay_max)

        self.stdout.write(
            self.style.SUCCESS(
                'Catálogo básico finalizado: '
                f"{stats['created']} criados, {stats['updated']} atualizados, {stats['skipped']} ignorados, {stats['errors']} erros."
            )
        )

    def _load_terms(self, input_path: Path) -> list[str]:
        terms: list[str] = []
        for raw_line in input_path.read_text(encoding='utf-8').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            term = line.split('|', 1)[0].strip()
            if term:
                terms.append(term)
        return terms

    def _upsert_catalog_product(self, item: dict, search_term: str) -> tuple[ProductCatalog, bool]:
        product_url = self._clean_text(item.get('product_url') or item.get('url'))
        title = self._clean_text(item.get('title'))

        if not product_url:
            raise CommandError(f'Produto sem URL encontrado para o termo "{search_term}".')
        if not title:
            raise CommandError(f'Produto sem título encontrado para o termo "{search_term}".')

        defaults = {
            'title': title,
            'description': self._clean_text(item.get('description')),
            'price': self._parse_price(item.get('price')),
            'image_url': self._clean_text(item.get('image_url') or item.get('image')),
            'store': self._clean_text(item.get('store')) or 'Amazon Brasil',
            'category': self._clean_text(item.get('category')),
            'search_term': self._clean_text(search_term),
            'is_essential_template': True,
        }

        product, created = ProductCatalog.objects.update_or_create(
            product_url=product_url,
            defaults=defaults,
        )
        return product, created

    def _parse_price(self, value) -> Decimal | None:
        text = self._clean_text(value)
        if not text or 'indisponivel' in text.lower():
            return None
        return parse_money_value(text)

    def _clean_text(self, value) -> str:
        return ' '.join(str(value or '').split()).strip()

    def _sleep_between_requests(self, delay_min: float, delay_max: float) -> None:
        if delay_max <= 0:
            return
        time.sleep(random.uniform(delay_min, delay_max))