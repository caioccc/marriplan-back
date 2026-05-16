import cloudinary
import cloudinary.uploader
from rest_framework import (permissions, status)
from rest_framework.decorators import (api_view, parser_classes,
                                       permission_classes)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.models import (WeddingImage)
from app.serializers import (WeddingImageSerializer)


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
        return Response({'error': 'Erro ao deletar imagem no Cloudinary.'}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
