import uuid
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import (filters, permissions, status, viewsets)
from rest_framework.decorators import (action, api_view, permission_classes)
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from app.models import (WeddingSite,
                        WeddingSiteHistory)
from app.serializers import (UserWeddingProfileSerializer,
                             WeddingSiteHistorySerializer,
                             WeddingSiteSerializer)
from app.utils import notify_user_wedding_site


class WeddingSiteViewSet(viewsets.ModelViewSet):
    serializer_class = WeddingSiteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WeddingSite.objects.filter(user=self.request.user)

    def get_object(self):
        try:
            return WeddingSite.objects.get(user=self.request.user)
        except WeddingSite.DoesNotExist:
            return None

    def list(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        user = request.user
        profile = getattr(user, 'wedding_profile', None)
        req_data = request.data.copy()
        if profile and (profile.nome_noivo or profile.nome_noiva):
            from django.utils.text import slugify
            base = f"{profile.nome_noivo or ''}-{profile.nome_noiva or ''}".strip('-').replace(' ', '-').lower()
            slug = slugify(base)
            original_slug = slug
            i = 1
            while WeddingSite.objects.filter(url_slug=slug).exists():
                slug = f"{original_slug}-{i}"
                i += 1
            req_data['url_slug'] = slug
        else:
            req_data['url_slug'] = str(uuid.uuid4())[:8]
        req_data['user'] = user.id
        serializer = self.get_serializer(data=req_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Histórico de criação
        site = WeddingSite.objects.get(pk=serializer.instance.pk)

        WeddingSiteHistory.objects.create(site=site, action='create', performed_by=user,
                                          snapshot=WeddingSiteSerializer(site).data)
        notify_user_wedding_site(request.user, 'create')
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def publish(self, request):
        site = self.get_object()
        if not site:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        site.status = 'published'
        site.last_published_at = timezone.now()
        site.save()
        WeddingSiteHistory.objects.create(site=site, action='publish', performed_by=request.user,
                                          snapshot=WeddingSiteSerializer(site).data)
        return Response({'status': 'published'})

    @action(detail=False, methods=['post'])
    def unpublish(self, request):
        site = self.get_object()
        if not site:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        site.status = 'draft'
        site.save()
        WeddingSiteHistory.objects.create(site=site, action='unpublish', performed_by=request.user,
                                          snapshot=WeddingSiteSerializer(site).data)
        return Response({'status': 'draft'})

    @action(detail=False, methods=['get'])
    def metrics(self, request):
        site = self.get_object()
        if not site:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        return Response({
            'visits': site.visits,
            'rsvp_count': site.rsvp_count,
            'rsvp_conversion': site.rsvp_conversion,
            'last_visitor': site.last_visitor,
            'last_visitor_at': site.last_visitor_at,
        })

    @action(detail=False, methods=['get'])
    def preview(self, request):
        site = self.get_object()
        if not site:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        # Retorna todos os campos relevantes do modelo
        return Response(WeddingSiteSerializer(site).data)

    def update(self, request, *args, **kwargs):
        # Atualiza o WeddingSite do usuário autenticado
        instance = self.get_object()
        if not instance:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        data = request.data.copy()
        data['url_slug'] = instance.url_slug  # Mantém o slug existente
        data['user'] = instance.user.id
        # Atualiza galeria se vier IDs
        gallery_ids = data.pop('gallery', None)
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if gallery_ids is not None:
            instance.gallery.set(gallery_ids)
        WeddingSiteHistory.objects.create(site=instance, action='edit', performed_by=request.user,
                                          snapshot=WeddingSiteSerializer(instance).data)
        notify_user_wedding_site(request.user, 'update')
        return Response(serializer.data)


class WeddingSiteHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WeddingSiteHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description', 'action']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = WeddingSiteHistory.objects.filter(site__user=user)
        # Filtros por período
        period = self.request.query_params.get('period')
        if period == 'today':
            queryset = queryset.filter(created_at__date=timezone.now().date())
        elif period == '7d':
            queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(days=7))
        elif period == '30d':
            queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(days=30))
        elif period == 'custom':
            start = self.request.query_params.get('start')
            end = self.request.query_params.get('end')
            if start and end:
                queryset = queryset.filter(created_at__date__gte=start, created_at__date__lte=end)
        return queryset


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_wedding_site(request, slug):
    try:
        site = get_object_or_404(WeddingSite, url_slug=slug)
        if site.status != 'published':
            return Response({'detail': 'Site não publicado.'}, status=404)
        user = site.user
        # Incrementa visitas
        site.visits += 1
        site.save(update_fields=['visits'])
        data = WeddingSiteSerializer(site).data
        data['user'] = user.username
        data['wedding_profile'] = UserWeddingProfileSerializer(user.wedding_profile).data if hasattr(user,
                                                                                                     'wedding_profile') else None
        return Response(data)
    except Exception as e:
        import logging
        logging.exception(f"Erro ao acessar site público: {slug}")
        return Response({'detail': 'Site não encontrado ou indisponível.'}, status=404)
