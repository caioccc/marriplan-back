import warnings
from urllib.parse import quote_plus

from pinterest_dl import PinterestDL


def normalize_query(value):
    text = str(value or '').strip().replace('_', ' ').replace('-', ' ')
    return ' '.join(text.split())


def build_inspiration_query(selected_style='', dress_code='', extra_terms=''):
    parts = [normalize_query(selected_style), normalize_query(dress_code), normalize_query(extra_terms)]
    parts = [part for part in parts if part]
    if not parts:
        return ''
    return ' casamento '.join([parts[0], ' '.join(parts[1:])]) if len(parts) > 1 else f'{parts[0]} casamento'


def _extract_value(item, keys, default=''):
    for key in keys:
        if isinstance(item, dict) and item.get(key):
            return item.get(key)
        if hasattr(item, key):
            value = getattr(item, key)
            if value:
                return value
    return default


def normalize_image_item(item, query=''):
    if isinstance(item, str):
        image_url = item
        source_url = item
        title = ''
        description = ''
        source_id = ''
        thumbnail_url = item
        metadata = {'raw': item}
    else:
        image_url = _extract_value(item, ['image_url', 'url', 'src', 'images'])
        if isinstance(image_url, dict):
            image_url = _extract_value(image_url, ['url', 'src'])
        thumbnail_url = _extract_value(item, ['thumbnail_url', 'thumbnail', 'image_url', 'url', 'src'])
        source_url = _extract_value(item, ['source_url', 'link', 'pin_url', 'url'])
        title = _extract_value(item, ['title', 'alt', 'name'])
        description = _extract_value(item, ['description', 'text', 'caption'])
        source_id = str(_extract_value(item, ['id', 'source_id', 'pin_id', 'image_id'], ''))
        metadata = item if isinstance(item, dict) else {
            'title': title,
            'description': description,
            'source_url': source_url,
        }

    image_url = image_url or source_url or thumbnail_url or ''
    thumbnail_url = thumbnail_url or image_url

    return {
        'source_id': source_id,
        'title': title,
        'description': description,
        'image_url': image_url,
        'thumbnail_url': thumbnail_url,
        'source_url': source_url,
        'query': query,
        'metadata': metadata,
    }


def get_images(query, num_images=50):
    try:
        images = PinterestDL.with_api().search(
            query=query,
            num=num_images,
            min_resolution=(200, 200),
            delay=0.4,
        )
    except Exception as e:
        warnings.warn(f'Erro ao buscar imagens no Pinterest: {e}')
        return []

    return [normalize_image_item(item, query=query) for item in images]
