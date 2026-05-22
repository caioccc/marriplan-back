from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import UserWeddingProfile, WeddingIdentity, WeddingIdentityInspiration, WeddingIdentityShareToken
from app.serializers import WeddingIdentityInspirationSerializer
from app.services.pinterest_service import build_inspiration_query, get_images


class ItemsPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50


class WeddingIdentityInspirationViewSet(viewsets.ModelViewSet):
    serializer_class = WeddingIdentityInspirationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_profile(self, create=False):
        profile = getattr(self.request.user, 'wedding_profile', None)
        if profile or not create:
            return profile
        profile, _ = UserWeddingProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_queryset(self):
        profile = self.get_profile()
        if not profile:
            return WeddingIdentityInspiration.objects.none()
        return WeddingIdentityInspiration.objects.filter(wedding_profile=profile)

    def _get_identity(self):
        profile = self.get_profile()
        if not profile:
            return None
        return getattr(profile, 'wedding_identity', None)

    def _require_identity(self):
        identity = self._get_identity()
        if not identity or not identity.selected_style or not identity.dress_code:
            raise ValidationError('Selecione estilo e dress code antes de acessar as inspirações.')
        return identity

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        profile = self.get_profile(create=True)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        source_id = payload.get('source_id') or ''
        image_url = payload.get('image_url')

        defaults = {
            'title': payload.get('title', ''),
            'description': payload.get('description', ''),
            'thumbnail_url': payload.get('thumbnail_url', ''),
            'source_url': payload.get('source_url', ''),
            'query': payload.get('query', ''),
            'selected_style': payload.get('selected_style', ''),
            'dress_code': payload.get('dress_code', ''),
            'is_favorite': payload.get('is_favorite', False),
            'is_liked': payload.get('is_liked', False),
            'metadata': payload.get('metadata', {}),
        }

        inspiration = None
        if source_id:
            inspiration, _ = WeddingIdentityInspiration.objects.get_or_create(
                wedding_profile=profile,
                source_id=source_id,
                defaults={**defaults, 'image_url': image_url},
            )
        if inspiration is None:
            inspiration, _ = WeddingIdentityInspiration.objects.get_or_create(
                wedding_profile=profile,
                image_url=image_url,
                defaults={**defaults, 'source_id': source_id},
            )

        for field_name, field_value in defaults.items():
            setattr(inspiration, field_name, field_value)
        inspiration.wedding_profile = profile
        inspiration.image_url = image_url
        if source_id:
            inspiration.source_id = source_id
        inspiration.save()
        return Response(self.get_serializer(inspiration).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        identity = self._get_identity()
        selected_style = request.query_params.get('selected_style') or (identity.selected_style if identity else '')
        dress_code = request.query_params.get('dress_code') or (identity.dress_code if identity else '')
        extra_terms = request.query_params.get('query') or request.query_params.get('terms') or ''

        query = build_inspiration_query(selected_style, dress_code, extra_terms)
        if not query:
            raise ValidationError('Selecione estilo e dress code para buscar inspirações.')

        images = get_images(query, num_images=50)
        return Response({
            'query': query,
            'count': len(images),
            'results': images,
        })


class PublicWeddingIdentityView(APIView):
    # Libera o acesso para qualquer pessoa sem exigir token JWT/Sessão
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            share_token = WeddingIdentityShareToken.objects.select_related('wedding_profile').get(token=token)
            profile = share_token.wedding_profile
            identity = WeddingIdentity.objects.get(wedding_profile=profile)
            inspirations = WeddingIdentityInspiration.objects.filter(wedding_profile=profile)

            # Monta o payload de retorno contendo os dados e o mural unificados
            return Response({
                "selected_style": identity.selected_style,
                "dress_code": identity.dress_code,
                "wedding_size": identity.wedding_size,
                "palette": identity.palette,  # Supondo que seja um JSONField ou relacionado
                "inspirations": WeddingIdentityInspirationSerializer(inspirations, many=True).data
            })
        except WeddingIdentityShareToken.DoesNotExist:
            return Response({"detail": "Não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except WeddingIdentity.DoesNotExist:
            return Response({"detail": "Não encontrado."}, status=status.HTTP_404_NOT_FOUND)
