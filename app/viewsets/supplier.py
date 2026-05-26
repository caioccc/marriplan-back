import random

from django.db.models import Q
from rest_framework import filters, permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response

from app.models import Supplier, SupplierCategory, WeddingSupplier
from app.serializers import (
    SupplierCategorySerializer,
    SupplierSerializer,
    WeddingSupplierSerializer,
)
from app.logging_utils import audit_log
from app.utils import MAX_SUPPLIERS_PER_SCOPE, is_limit_reached


from rest_framework.pagination import PageNumberPagination

class TwelveItemsPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100


class SupplierCategoryViewSet(viewsets.ModelViewSet):
    queryset = SupplierCategory.objects.all()
    serializer_class = SupplierCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'slug']
    ordering = ['name']


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.select_related('category', 'created_by_user').all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]

    pagination_class = TwelveItemsPagination
    
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'company_name', 'description', 'city', 'state', 'category__name']
    ordering_fields = ['?']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        seed = request.query_params.get('seed')

        if seed:
            items = list(queryset)
            random.Random(seed).shuffle(items)
            page = self.paginate_queryset(items)
        else:
            page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        category = self.request.query_params.get('category')
        state = self.request.query_params.get('state')
        city = self.request.query_params.get('city')
        status_param = self.request.query_params.get('status')
        featured = self.request.query_params.get('featured')

        if not user.is_staff and not user.is_superuser:
            queryset = queryset.filter(
                Q(status=Supplier.STATUS_APPROVED, visibility=Supplier.VISIBILITY_GLOBAL) |
                Q(created_by_user=user)
            )

        if category:
            queryset = queryset.filter(category__slug=category)
        if state:
            queryset = queryset.filter(state__icontains=state)
        if city:
            queryset = queryset.filter(city__icontains=city)
        if status_param:
            queryset = queryset.filter(status=status_param)
        if featured in {'1', 'true', 'True'}:
            queryset = queryset.filter(is_featured=True)

        return queryset

    def perform_create(self, serializer):
        visibility = Supplier.VISIBILITY_GLOBAL if self.request.user.is_staff or self.request.user.is_superuser else Supplier.VISIBILITY_SOLO
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            current_count = Supplier.objects.filter(created_by_user=self.request.user).count()
            if is_limit_reached(current_count, MAX_SUPPLIERS_PER_SCOPE):
                raise ValidationError({'detail': 'Limite de 50 fornecedores atingido.'})
        instance = serializer.save(created_by_user=self.request.user, visibility=visibility)
        audit_log('supplier.create', user=self.request.user, obj=instance, message='Fornecedor criado')

    def perform_update(self, serializer):
        instance = serializer.instance
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            updated = serializer.save(visibility=instance.visibility)
        else:
            updated = serializer.save()
        audit_log('supplier.update', user=self.request.user, obj=updated, message='Fornecedor atualizado')

    def perform_destroy(self, instance):
        audit_log('supplier.delete', user=self.request.user, obj=instance, message='Fornecedor removido')
        instance.delete()


class WeddingSupplierViewSet(viewsets.ModelViewSet):
    serializer_class = WeddingSupplierSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['supplier__name', 'supplier__company_name', 'supplier__description', 'notes', 'supplier__city', 'supplier__state']
    ordering_fields = ['updated_at', 'contract_date', 'wedding_delivery_date', 'estimated_price', 'negotiated_price', 'paid_amount', 'status']
    ordering = ['-is_favorite', '-updated_at']

    def get_queryset(self):
        user = self.request.user
        wedding_profile = getattr(user, 'wedding_profile', None)
        if not wedding_profile:
            return WeddingSupplier.objects.none()

        queryset = WeddingSupplier.objects.select_related('supplier', 'supplier__category', 'wedding').filter(wedding=wedding_profile)
        status_param = self.request.query_params.get('status')
        supplier_id = self.request.query_params.get('supplier')
        favorite = self.request.query_params.get('favorite')
        hired = self.request.query_params.get('hired')

        if status_param:
            queryset = queryset.filter(status=status_param)
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        if favorite in {'1', 'true', 'True'}:
            queryset = queryset.filter(is_favorite=True)
        if hired in {'1', 'true', 'True'}:
            queryset = queryset.filter(is_hired=True)

        return queryset

    def perform_create(self, serializer):
        wedding_profile = getattr(self.request.user, 'wedding_profile', None)
        if not wedding_profile:
            raise ValidationError({'detail': 'Usuário sem perfil de casamento.'})
        current_count = WeddingSupplier.objects.filter(wedding=wedding_profile).count()
        if is_limit_reached(current_count, MAX_SUPPLIERS_PER_SCOPE):
            raise ValidationError({'detail': 'Limite de 50 fornecedores atingido.'})
        instance = serializer.save(wedding=wedding_profile)
        audit_log('wedding_supplier.create', user=self.request.user, obj=instance, message='Fornecedor vinculado ao casamento')

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.status in {WeddingSupplier.STATUS_HIRED, WeddingSupplier.STATUS_PAID}:
            instance.is_hired = True
        elif instance.status == WeddingSupplier.STATUS_CANCELED:
            instance.is_hired = False
        instance.save(update_fields=['is_hired', 'updated_at'])
        audit_log('wedding_supplier.update', user=self.request.user, obj=instance, message='Vínculo de fornecedor atualizado')

    def perform_destroy(self, instance):
        audit_log('wedding_supplier.delete', user=self.request.user, obj=instance, message='Vínculo de fornecedor removido')
        instance.delete()

    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'count': queryset.count(),
        })

    @action(detail=False, methods=['post'], url_path='select')
    def select(self, request):
        wedding_profile = getattr(request.user, 'wedding_profile', None)
        if not wedding_profile:
            return Response({'detail': 'Usuário sem perfil de casamento.'}, status=status.HTTP_400_BAD_REQUEST)

        supplier_id = request.data.get('supplier_id')
        if not supplier_id:
            return Response({'detail': 'supplier_id é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            supplier = Supplier.objects.get(pk=supplier_id)
        except Supplier.DoesNotExist:
            return Response({'detail': 'Fornecedor não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        existing_relation = WeddingSupplier.objects.filter(wedding=wedding_profile, supplier=supplier).exists()
        if not existing_relation:
            current_count = WeddingSupplier.objects.filter(wedding=wedding_profile).count()
            if is_limit_reached(current_count, MAX_SUPPLIERS_PER_SCOPE):
                return Response({'detail': 'Limite de 50 fornecedores atingido.'}, status=status.HTTP_400_BAD_REQUEST)

        defaults = {
            'status': request.data.get('status') or WeddingSupplier.STATUS_QUOTING,
            'is_favorite': request.data.get('is_favorite') in {True, 'true', 'True', '1', 1},
            'is_hired': request.data.get('is_hired') in {True, 'true', 'True', '1', 1},
            'estimated_price': request.data.get('estimated_price') or None,
            'negotiated_price': request.data.get('negotiated_price') or None,
            'paid_amount': request.data.get('paid_amount') or None,
            'notes': request.data.get('notes', ''),
        }
        wedding_supplier, created = WeddingSupplier.objects.update_or_create(
            wedding=wedding_profile,
            supplier=supplier,
            defaults=defaults,
        )
        serializer = self.get_serializer(wedding_supplier)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
