from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from app.models import ProductCatalog
from app.utils import parse_money_value


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Importa o basic_products.json para o catálogo local de produtos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input-file',
            default=str(Path(settings.BASE_DIR) / 'basic_products.json'),
            help='Caminho do arquivo JSON de entrada.',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Remove itens do catálogo que não estiverem no JSON importado.',
        )

    def handle(self, *args, **options):
        input_file = Path(options['input_file'])
        if not input_file.exists():
            raise CommandError(f'Arquivo não encontrado: {input_file}')

        payload = self._load_payload(input_file)
        items = self._extract_items(payload)

        if not items:
            self.stdout.write(self.style.WARNING('Nenhum produto encontrado no JSON.'))
            return

        seen_urls: set[str] = set()
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
        }

        self.stdout.write(
            f'Importando {len(items)} produto(s) de {input_file} para ProductCatalog...'
        )

        for raw_item in items:
            stats['processed'] += 1
            normalized = self._normalize_item(raw_item)

            if normalized is None:
                stats['skipped'] += 1
                continue

            product_url = normalized['product_url']
            seen_urls.add(product_url)

            defaults = {
                'title': normalized['title'],
                'description': normalized['description'],
                'price': normalized['price'],
                'image_url': normalized['image_url'],
                'store': normalized['store'],
                'category': normalized['category'],
                'search_term': normalized['search_term'],
                'is_essential_template': normalized['is_essential_template'],
            }

            product, created = ProductCatalog.objects.update_or_create(
                product_url=product_url,
                defaults=defaults,
            )

            if created:
                stats['created'] += 1
            else:
                stats['updated'] += 1

            logger.debug('Produto importado: %s (%s)', product.title, product.product_url)

        if options['clear']:
            removed_count, _ = ProductCatalog.objects.exclude(product_url__in=seen_urls).delete()
            self.stdout.write(self.style.WARNING(f'Itens removidos fora do JSON: {removed_count}'))

        self.stdout.write(
            self.style.SUCCESS(
                'Importação finalizada: '
                f"{stats['created']} criados, {stats['updated']} atualizados, {stats['skipped']} ignorados."
            )
        )

    def _load_payload(self, input_file: Path):
        try:
            with input_file.open('r', encoding='utf-8') as json_file:
                return json.load(json_file)
        except json.JSONDecodeError as exc:
            raise CommandError(f'JSON inválido em {input_file}: {exc}') from exc

    def _extract_items(self, payload) -> list[dict]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if isinstance(payload, dict):
            for key in ('products', 'items', 'results'):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]

        return []

    def _normalize_item(self, raw_item: dict) -> dict | None:
        product_url = self._clean_text(raw_item.get('product_url') or raw_item.get('url') or raw_item.get('link'))
        title = self._clean_text(raw_item.get('title') or raw_item.get('name'))

        if not product_url or not title:
            return None

        return {
            'product_url': product_url,
            'title': title,
            'description': self._clean_text(raw_item.get('description')),
            'price': self._parse_price(raw_item.get('price')),
            'image_url': self._clean_text(raw_item.get('image_url') or raw_item.get('image')),
            'store': self._clean_text(raw_item.get('store')) or 'Amazon Brasil',
            'category': self._clean_text(raw_item.get('category')),
            'search_term': self._clean_text(raw_item.get('search_term') or raw_item.get('searchTerm')),
            'is_essential_template': bool(raw_item.get('is_essential_template', True)),
        }

    def _parse_price(self, value) -> Decimal | None:
        return parse_money_value(value)

    def _clean_text(self, value) -> str:
        if value is None:
            return ''

        return str(value).strip()