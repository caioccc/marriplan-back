# app/viewsets/chat.py — endpoints de ChatMessage, streaming, IA.
import uuid

from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import (permissions, status, viewsets)
from rest_framework.decorators import (action, api_view, permission_classes)
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from app.core.models.llm.chat import (ChatRequest, generate_streaming_response,
                                      prepare_chat_messages)
from app.core.renderers import EventStreamRenderer
from app.models import (ChatMessage, Notification, UserSession)
from app.serializers import (ChatMessageSerializer,
                             UserSessionSerializer)


@api_view(['delete'])
@permission_classes([permissions.IsAuthenticated])
def delete_all_sessions(request):
    UserSession.objects.filter(user=request.user).delete()
    return Response({'message': 'Todas as sessões foram excluídas.'}, status=200)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_all_messages(request):
    ChatMessage.objects.filter(session__user=request.user).delete()
    Notification.objects.create(
        user=request.user,
        type='warning',
        title='Mensagens removidas',
        message='Todas as suas mensagens foram removidas.',
        is_read=False
    )
    return Response({'message': 'Todas as mensagens foram excluídas.'}, status=200)


class UserSessionViewSet(viewsets.ModelViewSet):
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return UserSession.objects.filter(user=self.request.user)
        return UserSession.objects.none()

    def perform_create(self, serializer):
        existing_session = UserSession.objects.filter(
            user=self.request.user,
            messages__isnull=True
        ).first()

        if existing_session:
            existing_session.session_id = str(uuid.uuid4())
            existing_session.updated_at = timezone.now()
            existing_session.save()
            self.existing_session = existing_session
        else:
            session_id = str(uuid.uuid4())
            serializer.validated_data['session_id'] = session_id
            serializer.validated_data['title'] = f"Sessão Inicial - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self.existing_session = serializer.save(user=self.request.user)
            # criar mensagem default da IA
            ChatMessage.objects.create(
                session=self.existing_session,
                is_user=False,
                content=(
                    "Olá! 👋 Eu sou o seu assistente virtual do **Marriplan**, aqui para ajudar você a organizar cada detalhe do seu casamento perfeito!\n\n"
                    "Você pode me perguntar sobre:\n"
                    "- ✅ Checklist pré-casamento (12 meses)\n"
                    "- ✅ Configuração de RSVP e confirmação de presença\n"
                    "- ✅ Lista de presentes e organização de convidados\n"
                    "- ✅ Agenda do dia do casamento\n"
                    "- ✅ Dicas de fornecedores, decoração e muito mais!\n\n"
                    "**Como posso ajudar você hoje?**  \n"
                    "Exemplos:\n\n"
                    "- \"Como montar um checklist de 12 meses?\"\n"
                    "- \"Preciso de ideias para uma lista de presentes criativa.\"\n"
                    "- \"Como criar um formulário de RSVP eficaz?\""
                )
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # Valida os dados antes de acessar validated_data
        self.perform_create(serializer)
        return Response(
            UserSessionSerializer(self.existing_session).data,
            status=status.HTTP_200_OK if hasattr(self, 'existing_session') else status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['delete'], url_path='delete-by-session-id/(?P<session_id>[^/]+)',
            permission_classes=[permissions.IsAuthenticated])
    def delete_by_session_id(self, request, session_id=None):
        if not session_id:
            return Response({"error": "session_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = UserSession.objects.get(session_id=session_id, user=request.user)
            session.delete()
            return Response({"message": "Session deleted successfully."}, status=status.HTTP_200_OK)
        except UserSession.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)


class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return ChatMessage.objects.filter(session__user=self.request.user)
        return ChatMessage.objects.none()

    def partial_update(self, request, pk=None):
        user = request.user
        try:
            message = ChatMessage.objects.get(pk=pk, session__user=user)
        except ChatMessage.DoesNotExist:
            return Response({"error": "Mensagem não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        new_content = request.data.get("content")
        if not new_content:
            return Response({"error": "Conteúdo é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        # remove a mensagem
        ChatMessage.objects.filter(pk=pk).delete()

        # Remove mensagens posteriores na mesma sessão
        ChatMessage.objects.filter(
            session=message.session,
            created_at__gt=message.created_at
        ).delete()

        return Response(ChatMessageSerializer(message).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='update-title', permission_classes=[permissions.IsAuthenticated])
    def update_title(self, request, session_id=None):
        try:
            session = UserSession.objects.get(session_id=session_id, user=request.user)
        except UserSession.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        new_title = request.data.get('title')
        if not new_title:
            return Response({"error": "Title is required."}, status=status.HTTP_400_BAD_REQUEST)

        session.title = new_title
        session.save()

        return Response({"message": "Title updated successfully.", "session": UserSessionSerializer(session).data},
                        status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='stream-message', permission_classes=[permissions.IsAuthenticated],
            parser_classes=[JSONParser],
            renderer_classes=[EventStreamRenderer, JSONRenderer])
    def stream_message(self, request):
        session_id = request.data.get('session_id')
        user_message = request.data.get('content')

        if not session_id or not user_message:
            return Response({"error": "session_id and content are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = UserSession.objects.get(session_id=session_id, user=request.user)
        except UserSession.DoesNotExist:
            return Response({"error": "Invalid session_id."}, status=status.HTTP_404_NOT_FOUND)

        # Fetch the chat history for the session
        chat_history = ChatMessage.objects.filter(session=session).order_by('created_at')
        history = [
            {"role": "user" if msg.is_user else "assistant", "content": msg.content}
            for msg in chat_history
        ]

        # Preservar mensagem original
        original_message = user_message

        # Detectar intenção do usuário
        intent = self._detect_intent(user_message, session)

        # Se for pedido de questão, processar antes
        if intent['type'] == 'request_question':
            context = self._handle_question_request(intent['filters'], session, request.user)
            if context:
                # Adicionar contexto à mensagem para a LLM
                user_message = f"{context}\n\nMensagem original do usuário: {user_message}"

        # Se for resposta a questão, verificar
        elif intent['type'] == 'answer_question':
            context = self._handle_answer(intent['answer'], session, request.user)
            if context:
                user_message = f"{context}\n\nResposta do usuário: {intent['answer']}"

        # Se for referência a questão anterior
        elif intent['type'] == 'reference_previous_question':
            context = self._handle_question_reference(intent, session, request.user)
            if context:
                user_message = f"{context}\n\nMensagem original: {user_message}"

        # Prepare chat messages
        chat_request = ChatRequest(current_message=user_message, history=history)
        chat_messages = prepare_chat_messages(chat_request)

        # Stream response
        response = StreamingHttpResponse(
            generate_streaming_response(chat_messages, session, original_message),
            content_type="text/event-stream"
        )
        response['Cache-Control'] = 'no-cache'
        return response

    @action(detail=False, methods=['post'], url_path='send-message', permission_classes=[permissions.IsAuthenticated])
    def send_message(self, request):
        session_id = request.data.get('session_id')
        user_message = request.data.get('content')

        if not session_id or not user_message:
            return Response({"error": "session_id and content are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = UserSession.objects.get(session_id=session_id, user=request.user)
        except UserSession.DoesNotExist:
            return Response({"error": "Invalid session_id."}, status=status.HTTP_404_NOT_FOUND)

        # Save the user's message
        user_chat_message = ChatMessage.objects.create(
            session=session,
            is_user=True,
            content=user_message
        )

        # Simulate an AI response
        ai_response = f"Response to: {user_message}"

        # Save the AI's response
        ai_chat_message = ChatMessage.objects.create(
            session=session,
            is_user=False,
            content=ai_response
        )

        return Response({
            "user_message": ChatMessageSerializer(user_chat_message).data,
            "ai_response": ChatMessageSerializer(ai_chat_message).data
        }, status=status.HTTP_201_CREATED)

    def _detect_intent(self, message: str, session: UserSession) -> dict:
        """
        Detecta a intenção do usuário na mensagem para contexto de planejamento de casamentos.
        """
        message_lower = message.lower()

        # Palavras-chave de cada área do planejamento de casamento
        checklist_keywords = ["checklist", "pré-casamento", "preparativos", "12 meses", "organizar casamento"]
        rsvp_keywords = ["rsvp", "confirmação de presença", "confirmar presença", "lista de convidados"]
        presentes_keywords = ["lista de presentes", "presentes", "sugestão de presentes", "gift list"]
        agenda_keywords = ["agenda", "cronograma", "horário", "programação", "roteiro do dia"]
        fornecedores_keywords = ["fornecedor", "buffet", "decoração", "fotógrafo", "dj", "cerimonial", "local",
                                 "orçamento", "contratar", "serviço"]
        dicas_keywords = ["dica", "ideia", "inspiração", "cerimônia", "festa", "decoração", "tema", "tendência"]

        # Detectar intenção principal
        if any(word in message_lower for word in checklist_keywords):
            return {"type": "checklist"}
        if any(word in message_lower for word in rsvp_keywords):
            return {"type": "rsvp"}
        if any(word in message_lower for word in presentes_keywords):
            return {"type": "presentes"}
        if any(word in message_lower for word in agenda_keywords):
            return {"type": "agenda"}
        if any(word in message_lower for word in fornecedores_keywords):
            return {"type": "fornecedores"}
        if any(word in message_lower for word in dicas_keywords):
            return {"type": "dicas"}

        # Se não encontrou, retorna como chat genérico
        return {"type": "chat"}

    def _extract_filters(self, message: str) -> dict:
        """
        Extrai filtros da mensagem do usuário para contexto de casamento.
        """
        filters = {}
        # Exemplo: detectar mês, número de convidados, tipo de cerimônia, orçamento, etc.
        import re

        # Detectar número de convidados
        convidados_match = re.search(r'(\d+)\s*(convidados|pessoas)', message)
        if convidados_match:
            filters['convidados'] = int(convidados_match.group(1))
        # Detectar orçamento
        orcamento_match = re.search(r'\b(R\$|reais|mil)\s*(\d+[\.,]?\d*)', message)
        if orcamento_match:
            filters['orcamento'] = orcamento_match.group(0)
        # Detectar mês ou data
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
                 "novembro", "dezembro"]
        for mes in meses:
            if mes in message:
                filters['mes'] = mes
                break
        return filters

    def _handle_question_request(self, filters: dict, session: UserSession, user) -> str:
        """
        Processa pedido de informação sobre planejamento de casamento e retorna contexto para a LLM.
        """
        # Exemplo de contexto para a LLM baseado nos filtros extraídos
        context_lines = []
        if 'convidados' in filters:
            context_lines.append(f"O usuário informou que terá cerca de {filters['convidados']} convidados.")
        if 'orcamento' in filters:
            context_lines.append(f"O orçamento estimado informado pelo usuário é {filters['orcamento']}.")
        if 'mes' in filters:
            context_lines.append(f"O casamento está previsto para o mês de {filters['mes']}.")

        # Adicionar instrução para a LLM
        context_lines.append(
            "Lembre-se: Responda de forma prática, objetiva e sempre focada em planejamento de casamentos. "
            "Seja detalhado e traga dicas úteis para o usuário organizar o evento, conforme o filtro informado. "
            "Se não houver filtro, responda de forma geral sobre o tema solicitado."
        )
        return "\n".join(
            context_lines) if context_lines else "Responda de forma detalhada e prática sobre o tema de planejamento de casamentos solicitado pelo usuário."

    def _handle_answer(self, answer: str, session: UserSession, user) -> str:
        """
        Não há mais verificação de resposta de questão. Apenas retorna mensagem padrão.
        """
        return "Atualmente não há verificação de respostas, pois o assistente Marriplan não trabalha mais com perguntas e respostas de provas. Se precisar de ajuda com planejamento de casamento, envie sua dúvida!"

    def _handle_question_reference(self, intent: dict, session: UserSession, user) -> str:
        """
        Não há mais referência a questões anteriores. Retorna mensagem padrão.
        """
        return "O assistente Marriplan não mantém histórico de questões. Por favor, envie sua dúvida sobre planejamento de casamento."

    def _format_questions_summary(self, questions_history: list) -> str:
        """
        Não há mais resumo de questões. Função mantida apenas para compatibilidade.
        """
        return "(Sem histórico de questões. O assistente Marriplan responde apenas dúvidas sobre planejamento de casamento.)"

    def _format_knowledge_refs(self, refs: list) -> str:
        """
        Não há mais referências de conhecimento. Função mantida apenas para compatibilidade.
        """
        return "(Sem referências específicas. Para dicas e fornecedores, envie sua dúvida!)"
