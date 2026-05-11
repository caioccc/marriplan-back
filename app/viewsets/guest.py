import io

import pandas as pd
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from rest_framework import (permissions, status, viewsets, filters)
from rest_framework.decorators import (action)
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response


from app.models import (Guest)
from app.serializers import (GuestSerializer)


class GuestViewSet(viewsets.ModelViewSet):
    serializer_class = GuestSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        # Se for noivo(a) ou convidado, vê todos os convidados do casamento vinculado ao wedding_profile
        if hasattr(user, 'wedding_profile'):
            return Guest.objects.filter(wedding_profile=user.wedding_profile).order_by('-created_at')
        # Se for convidado (sem wedding_profile), mas está cadastrado como Guest, buscar o wedding_profile pelo Guest
        guest = Guest.objects.filter(user=user).first()
        if guest and guest.wedding_profile:
            return Guest.objects.filter(wedding_profile=guest.wedding_profile).order_by('-created_at')
        # Caso não tenha vínculo, retorna apenas o próprio cadastro
        return Guest.objects.filter(user=user).order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'wedding_profile'):
            serializer.save(user=user, wedding_profile=user.wedding_profile)
        else:
            serializer.save(user=user)

    @action(detail=False, methods=['get'], url_path='download-model')
    def download_model(self, request):
        # Modelo padrão CSV
        columns = ['name', 'phone', 'whatsapp', 'email', 'alergias', 'acompanhantes', 'observacoes']
        df = pd.DataFrame(columns=columns)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="modelo_convidados.csv"'
        df.to_csv(response, index=False)
        return response

    @action(detail=False, methods=['post'], url_path='import', parser_classes=[MultiPartParser, FormParser])
    def import_guests(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'Arquivo não enviado.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith('.xlsx'):
                df = pd.read_excel(file)
            else:
                return Response({'detail': 'Formato não suportado. Envie CSV ou Excel.'},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'detail': f'Erro ao ler arquivo: {e}'}, status=status.HTTP_400_BAD_REQUEST)
        errors = []
        created = 0
        for idx, row in df.iterrows():
            data = row.to_dict()
            data = {k: (v if pd.notnull(v) else None) for k, v in data.items()}
            # Normaliza campos opcionais: se vierem None, NaN ou vazio, vira string vazia
            for field in ['whatsapp', 'phone', 'alergias', 'acompanhantes', 'observacoes']:
                if field in data and (data[field] is None or str(data[field]).strip() == '' or pd.isna(data[field])):
                    data[field] = ''
            serializer = GuestSerializer(data=data)
            if serializer.is_valid():
                # Verifica duplicidade de e-mail
                wedding_profile = getattr(request.user, 'wedding_profile', None)
                if data.get('email') and Guest.objects.filter(email=data['email'],
                                                              wedding_profile=wedding_profile).exists():
                    errors.append({'row': idx + 2, 'error': 'E-mail duplicado'})
                    continue
                # Salva explicitamente user e wedding_profile
                if wedding_profile:
                    serializer.save(user=request.user, wedding_profile=wedding_profile)
                else:
                    serializer.save(user=request.user)
                created += 1
            else:
                errors.append({'row': idx + 2, 'error': serializer.errors})
        if errors:
            return Response(
                {'detail': f'{created} convidados importados. Alguns registros possuem erro.', 'errors': errors},
                status=status.HTTP_207_MULTI_STATUS)
        return Response({'detail': f'{created} convidados importados com sucesso.'})

    @action(detail=False, methods=['get'], url_path='export')
    def export_guests(self, request):
        format = request.query_params.get('format', 'pdf')
        queryset = self.filter_queryset(self.get_queryset())
        data = GuestSerializer(queryset, many=True).data
        df = pd.DataFrame(data)
        df['status_rsvp'] = ''
        df['grupo'] = ''
        if format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="convidados.csv"'
            df.to_csv(response, index=False)
            return response
        elif format == 'xlsx':
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="convidados.xlsx"'
            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            return response
        elif format == 'pdf':
            try:
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="convidados.pdf"'
                buffer = io.BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                y = height - 40
                p.setFont('Helvetica-Bold', 14)
                p.drawString(40, y, 'Lista de Convidados')
                y -= 30
                p.setFont('Helvetica', 10)
                # Cabeçalho
                columns = ['Nome', 'Telefone', 'Acompanhantes', 'Observações', 'Alergias']
                col_widths = [140, 80, 90, 120, 90]
                x = 40
                for i, col in enumerate(columns):
                    p.drawString(x, y, col)
                    x += col_widths[i]
                y -= 18
                # Linhas
                for _, row in df.iterrows():
                    x = 40
                    values = [
                        str(row.get('name', '')),
                        str(row.get('phone', '')),
                        str(row.get('acompanhantes', '')),
                        str(row.get('observacoes', '')),
                        str(row.get('alergias', '')),
                    ]
                    for i, value in enumerate(values):
                        p.drawString(x, y,
                                     value[:40] if i == 0 else value[:25])  # Permite nomes maiores na primeira coluna
                        x += col_widths[i]
                    y -= 15
                    if y < 60:
                        p.showPage()
                        y = height - 40
                        p.setFont('Helvetica', 10)
                p.save()
                pdf = buffer.getvalue()
                buffer.close()
                response.write(pdf)
                return response
            except Exception as e:
                return Response({'detail': f'Erro ao exportar PDF: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({'detail': 'Formato não suportado.'}, status=status.HTTP_400_BAD_REQUEST)
