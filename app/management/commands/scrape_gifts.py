from __future__ import annotations

import json
import logging
import random
import re
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from app.constants_gift import PRODUCTS_TO_SEARCH
from app.models import ProductCatalog
from app.utils import parse_money_value
from app.services.scrapers.amazon import AmazonScraper


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scrape gifts from marketplace search terms and store a local catalog.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit-per-term',
            type=int,
            default=12,
            help='Maximum products saved per search term.',
        )
        parser.add_argument(
            '--terms-limit',
            type=int,
            default=0,
            help='Optional cap for the number of search terms to process.',
        )
        parser.add_argument(
            '--delay-min',
            type=float,
            default=1.0,
            help='Minimum random delay between requests.',
        )
        parser.add_argument(
            '--delay-max',
            type=float,
            default=2.5,
            help='Maximum random delay between requests.',
        )
        parser.add_argument(
            '--output-json',
            default=str(Path(settings.BASE_DIR) / 'products.json'),
            help='Path of the JSON file that will receive the exported catalog.',
        )

    def handle(self, *args, **options):
        limit_per_term = max(1, options['limit_per_term'])
        delay_min = max(0.0, options['delay_min'])
        delay_max = max(delay_min, options['delay_max'])
        terms = self._build_term_queue()
        if options['terms_limit'] > 0:
            terms = terms[: options['terms_limit']]

        scraper = AmazonScraper(max_results=limit_per_term)
        exported_products: dict[str, dict] = {}

        logger.info(
            'Iniciando scrape_gifts para Amazon com %s termos, limite por termo=%s, delay=[%s, %s], output_json=%s',
            len(terms),
            limit_per_term,
            delay_min,
            delay_max,
            options['output_json'],
        )

        stats = {
            'terms': 0,
            'found': 0,
            'saved': 0,
            'updated': 0,
            'errors': 0,
        }

        self.stdout.write(
            self.style.SUCCESS(
                f'Iniciando scraper da Amazon com {len(terms)} termos.'
            )
        )

        for search_term in terms:
            stats['terms'] += 1
            self.stdout.write(f'Buscando "{search_term}" na Amazon...')
            logger.info('Processando termo %s/%s: "%s"', stats['terms'], len(terms), search_term)

            try:
                results = scraper.search_products(search_term, max_results=limit_per_term)
            except Exception as exc:
                stats['errors'] += 1
                logger.exception('Erro ao consultar Amazon para termo "%s"', search_term)
                self.stdout.write(self.style.WARNING(f'Falha na Amazon para "{search_term}": {exc}'))
                self._sleep_between_requests(delay_min, delay_max)
                continue

            stats['found'] += len(results)
            logger.info('Termo "%s" retornou %s resultado(s)', search_term, len(results))

            for item in results[:limit_per_term]:
                product, created = self._upsert_product(item, search_term=search_term)
                if product is None:
                    logger.debug('Item ignorado no termo "%s" por faltar URL ou título', search_term)
                    continue

                if created:
                    stats['saved'] += 1
                    logger.info('Produto criado: %s | %s', product.title, product.product_url)
                else:
                    stats['updated'] += 1
                    logger.info('Produto atualizado: %s | %s', product.title, product.product_url)

                exported_products[product.product_url] = self._serialize_product(product)

            self._sleep_between_requests(delay_min, delay_max)
            logger.debug('Pausa concluída após o termo "%s"', search_term)

        self._write_json(Path(options['output_json']), exported_products)

        logger.info(
            'scrape_gifts finalizado. terms=%s found=%s saved=%s updated=%s errors=%s exported=%s',
            stats['terms'],
            stats['found'],
            stats['saved'],
            stats['updated'],
            stats['errors'],
            len(exported_products),
        )

        self.stdout.write(
            self.style.SUCCESS(
                'Scrape finalizado: '
                f"{stats['saved']} criados, {stats['updated']} atualizados, {stats['errors']} erros, "
                f"{len(exported_products)} produtos exportados."
            )
        )

    def _build_term_queue(self) -> list[str]:
        return list(PRODUCTS_TO_SEARCH)

    def _upsert_product(self, item: dict, search_term: str) -> tuple[ProductCatalog | None, bool]:
        product_url = self._clean_url(item.get('product_url') or item.get('url'))
        if not product_url:
            logger.debug('Ignorando item sem product_url no termo "%s"', search_term)
            return None, False

        title = self._clean_text(item.get('title'))
        if not title:
            logger.debug('Ignorando item sem title para url %s no termo "%s"', product_url, search_term)
            return None, False

        defaults = {
            'title': title,
            'description': self._clean_text(item.get('description')),
            'price': self._parse_price(item.get('price')),
            'image_url': self._clean_url(item.get('image_url') or item.get('image')),
            'store': self._clean_text(item.get('store')) or 'Amazon Brasil',
            'category': self._clean_text(item.get('category')),
            'search_term': self._clean_text(search_term),
        }

        product = self._find_existing_product(product_url=product_url, title=title)
        if product is None:
            product = ProductCatalog.objects.create(
                product_url=product_url,
                **defaults,
            )
            return product, True

        product.title = defaults['title']
        product.description = defaults['description']
        product.price = defaults['price']
        product.image_url = defaults['image_url']
        product.product_url = product_url
        product.store = defaults['store']
        product.category = defaults['category']
        product.search_term = defaults['search_term']
        product.save()
        return product, False

    def _find_existing_product(self, product_url: str, title: str) -> ProductCatalog | None:
        product = ProductCatalog.objects.filter(product_url=product_url).first()
        if product is not None:
            return product

        return ProductCatalog.objects.filter(title__iexact=title).first()

    def _serialize_product(self, product: ProductCatalog) -> dict[str, object]:
        return {
            'title': product.title,
            'description': product.description,
            'price': str(product.price) if product.price is not None else None,
            'image_url': product.image_url,
            'product_url': product.product_url,
            'store': product.store,
            'category': product.category,
            'search_term': product.search_term,
            'created_at': product.created_at.isoformat() if product.created_at else None,
            'updated_at': product.updated_at.isoformat() if product.updated_at else None,
        }

    def _write_json(self, output_path: Path, exported_products: dict[str, dict]) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = sorted(
            exported_products.values(),
            key=lambda item: (item.get('store') or '', item.get('category') or '', item.get('title') or ''),
        )

        logger.info('Exportando %s produto(s) para JSON em %s', len(payload), output_path)
        with output_path.open('w', encoding='utf-8') as json_file:
            json.dump(payload, json_file, ensure_ascii=False, indent=2)

        logger.info('JSON exportado com sucesso em %s', output_path)
        self.stdout.write(self.style.SUCCESS(f'Arquivo JSON salvo em {output_path}'))

    def _clean_text(self, value) -> str:
        return re.sub(r'\s+', ' ', str(value or '')).strip()

    def _clean_url(self, value) -> str:
        return self._clean_text(value)

    def _parse_price(self, value) -> Decimal | None:
        text = self._clean_text(value)
        if not text or 'indisponivel' in text.lower():
            return None

        return parse_money_value(text)

    def _sleep_between_requests(self, delay_min: float, delay_max: float) -> None:
        if delay_max <= 0:
            return
        delay = random.uniform(delay_min, delay_max)
        logger.debug('Aguardando %.2f segundos antes da próxima requisição', delay)
        time.sleep(delay)
