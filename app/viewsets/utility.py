import cloudinary
import cloudinary.uploader
from django.db.models import Q
from rest_framework import (permissions, status)
from rest_framework.decorators import (api_view, parser_classes,
                                       permission_classes)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.models import (ProductCatalog, WeddingImage)
from app.services.scrapers.amazon import AmazonScraper
from app.serializers import (WeddingImageSerializer)


FEATURED_MARKETPLACE_CATEGORIES = [
    ('cozinha', 'Cozinha'),
    ('banheiro', 'Banheiro'),
    ('moveis', 'Móveis'),
    ('eletrodomesticos', 'Eletrodomésticos'),
]


def _upload_to_cloudinary(file, folder, resource_type='image'):
    kwargs = {
        'folder': folder,
        'resource_type': resource_type,
        'overwrite': True,
    }
    if resource_type == 'image':
        kwargs['transformation'] = [
            {'width': 1200, 'height': 600, 'crop': 'limit'} if folder == 'wedding-hero' else {'width': 600, 'height': 400, 'crop': 'limit'}
        ]
    return cloudinary.uploader.upload(file, **kwargs)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_cloudinary(request):
    file = request.FILES.get('file')
    folder = request.data.get('folder', 'wedding-site')
    if not file:
        return Response({'error': 'Arquivo não enviado.'}, status=status.HTTP_400_BAD_REQUEST)
    if file.size > 10 * 1024 * 1024:
        return Response({'error': 'A imagem deve ter no máximo 10MB.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = _upload_to_cloudinary(file, folder, resource_type='image')
        # Cria WeddingImage
        image = WeddingImage.objects.create(
            url=result['secure_url'],
            id_cloudinary=result['public_id'],
            folder=folder,
            in_use=True
        )
        return Response(WeddingImageSerializer(image).data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_cloudinary_file(request):
    file = request.FILES.get('file')
    folder = request.data.get('folder', 'supplier-contracts')
    if not file:
        return Response({'error': 'Arquivo não enviado.'}, status=status.HTTP_400_BAD_REQUEST)
    if file.size > 20 * 1024 * 1024:
        return Response({'error': 'O arquivo deve ter no máximo 20MB.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = _upload_to_cloudinary(file, folder, resource_type='auto')
        return Response({
            'url': result['secure_url'],
            'public_id': result['public_id'],
            'resource_type': result.get('resource_type', 'auto'),
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def delete_cloudinary_image(request):
    public_id = request.data.get('public_id')
    if not public_id:
        return Response({'error': 'public_id é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = cloudinary.uploader.destroy(public_id)
        if result.get('result') == 'ok':
            WeddingImage.objects.filter(id_cloudinary=public_id).delete()
            return Response({'status': 'deleted'})
        elif result.get('result') == 'not found':
            WeddingImage.objects.filter(id_cloudinary=public_id).delete()
            return Response({'status': 'not found, but record deleted'})
        return Response({'error': 'Erro ao deletar imagem no Cloudinary.'}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_marketplace_products(request):
    query = (request.query_params.get('q') or '').strip()
    max_results_raw = request.query_params.get('max_results', '12').strip()

    if not query:
        return Response({'detail': 'O parâmetro q é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        max_results = max(1, min(int(max_results_raw), 12))
    except ValueError:
        max_results = 12

    scraper = AmazonScraper(max_results=12)
    try:
        results = scraper.search_products(query, max_results=max_results)
    except Exception as exc:
        fallback_results = _search_catalog_products(query, max_results)
        return Response(
            {
                'query': query,
                'count': len(fallback_results),
                'results': fallback_results,
                'source': 'product_catalog',
                'detail': f'Amazon indisponível, retornando catálogo local: {exc}',
            }
        )

    return Response({'query': query, 'count': len(results), 'results': results})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def featured_marketplace_products(request):
    max_per_category_raw = request.query_params.get('max_per_category', '3').strip()

    try:
        max_per_category = max(1, min(int(max_per_category_raw), 12))
    except ValueError:
        max_per_category = 3

    results: list[dict] = []
    seen_urls: set[str] = set()

    for category_slug, category_label in FEATURED_MARKETPLACE_CATEGORIES:
        category_products = ProductCatalog.objects.filter(category__iexact=category_slug).order_by(
            '-created_at', 'store', 'title'
        )[:max_per_category]

        for product in category_products:
            product_url = (product.product_url or '').strip()
            if not product_url or product_url in seen_urls:
                continue

            title = (product.title or '').strip()
            if not title:
                continue

            seen_urls.add(product_url)
            results.append(
                {
                    'title': title,
                    'description': (product.description or '').strip(),
                    'price': str(product.price) if product.price is not None else None,
                    'image_url': (product.image_url or '').strip(),
                    'product_url': product_url,
                    'category': (product.category or category_slug).strip() or category_slug,
                    'category_label': category_label,
                    'store': (product.store or '').strip() or 'Catálogo local',
                }
            )

    if len(results) < max_per_category * len(FEATURED_MARKETPLACE_CATEGORIES):
        remaining = max_per_category * len(FEATURED_MARKETPLACE_CATEGORIES) - len(results)
        fallback_products = ProductCatalog.objects.exclude(product_url__in=seen_urls).order_by(
            '-created_at', 'store', 'title'
        )[:remaining]

        for product in fallback_products:
            product_url = (product.product_url or '').strip()
            if not product_url or product_url in seen_urls:
                continue

            title = (product.title or '').strip()
            if not title:
                continue

            seen_urls.add(product_url)
            results.append(
                {
                    'title': title,
                    'description': (product.description or '').strip(),
                    'price': str(product.price) if product.price is not None else None,
                    'image_url': (product.image_url or '').strip(),
                    'product_url': product_url,
                    'category': (product.category or '').strip(),
                    'store': (product.store or '').strip() or 'Catálogo local',
                }
            )

    return Response(
        {
            'query': 'featured_catalog',
            'count': len(results),
            'results': results,
            'source': 'product_catalog',
        }
    )


def _search_catalog_products(query: str, limit: int) -> list[dict]:
    normalized_query = query.lower()
    catalog = ProductCatalog.objects.filter(
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(category__icontains=query)
        | Q(store__icontains=query)
        | Q(search_term__icontains=query)
    )

    results = []
    seen_urls: set[str] = set()
    for product in catalog.order_by('-created_at', 'store', 'title'):
        if len(results) >= limit:
            break

        product_url = (product.product_url or '').strip()
        if product_url and product_url in seen_urls:
            continue

        if product_url:
            seen_urls.add(product_url)

        title = (product.title or '').strip()
        description = (product.description or '').strip()
        category = (product.category or '').strip()
        store = (product.store or '').strip()

        if not title:
            continue

        results.append(
            {
                'title': title,
                'description': description,
                'price': str(product.price) if product.price is not None else None,
                'image_url': (product.image_url or '').strip(),
                'product_url': product_url,
                'category': category or normalized_query,
                'store': store or 'Catálogo local',
            }
        )

    return results
