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
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type='image',
            overwrite=True,
            transformation=[{'width': 1200, 'height': 600, 'crop': 'limit'}] if folder == 'wedding-hero' else [
                {'width': 600, 'height': 400, 'crop': 'limit'}]
        )
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
