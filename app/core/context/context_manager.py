"""
Gerenciador principal de contexto
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from app.models import UserSession, ChatMessage
from .session_state import SessionState, SessionStatus
from .conversation_memory import ConversationMemory

logger = logging.getLogger(__name__)


@dataclass
class Context:
    """Contexto completo para processamento de mensagens"""
    session_state: SessionState
    conversation_memory: ConversationMemory
    current_message: str
    current_intent: Optional[Dict[str, Any]] = None
    django_session: Optional[UserSession] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte contexto para dicionário"""
        return {
            'session_id': self.session_state.session_id,
            'user_id': self.session_state.user_id,
            'status': self.session_state.status.value,
            'current_message': self.current_message,
            'current_intent': self.current_intent,
            'active_question_id': self.session_state.active_question.question_id if self.session_state.active_question else None,
            'last_action': self.session_state.last_action,
            'conversation_length': len(self.conversation_memory.entries),
            'metadata': self.metadata
        }


class ContextManager:
    """Gerenciador centralizado de contexto"""
    
    def __init__(self):
        """Inicializa o gerenciador de contexto"""
        self._contexts: Dict[str, Context] = {}
        self._session_states: Dict[str, SessionState] = {}
        self._memories: Dict[str, ConversationMemory] = {}
        logger.info("ContextManager inicializado")
    
    def get_or_create_context(self, session_id: str, user_id: str, 
                            django_session: Optional[UserSession] = None) -> Context:
        """
        Obtém ou cria contexto para uma sessão
        
        Args:
            session_id: ID da sessão
            user_id: ID do usuário
            django_session: Objeto UserSession do Django
            
        Returns:
            Context: Contexto da sessão
        """
        if session_id not in self._contexts:
            # Cria novo estado de sessão
            session_state = SessionState(
                session_id=session_id,
                user_id=user_id
            )
            self._session_states[session_id] = session_state
            
            # Cria nova memória
            memory = ConversationMemory()
            self._memories[session_id] = memory
            
            # Sincroniza com Django se disponível
            if django_session:
                self._sync_from_django(session_state, memory, django_session)
            
            # Cria contexto
            context = Context(
                session_state=session_state,
                conversation_memory=memory,
                current_message="",
                django_session=django_session
            )
            self._contexts[session_id] = context
            
            logger.info(f"Novo contexto criado para sessão {session_id}")
        else:
            context = self._contexts[session_id]
            # Atualiza referência do Django se fornecida
            if django_session:
                context.django_session = django_session
        
        return context
    
    def update_context(self, session_id: str, message: str, 
                      intent: Optional[Dict[str, Any]] = None) -> Context:
        """
        Atualiza contexto com nova mensagem
        
        Args:
            session_id: ID da sessão
            message: Nova mensagem
            intent: Intenção detectada (opcional)
            
        Returns:
            Context: Contexto atualizado
        """
        if session_id not in self._contexts:
            raise ValueError(f"Contexto não encontrado para sessão {session_id}")
        
        context = self._contexts[session_id]
        context.current_message = message
        context.current_intent = intent
        
        # Atualiza intent no estado
        if intent:
            context.session_state.current_intent = intent.get('type')
        
        return context
    
    def add_message_to_memory(self, session_id: str, role: str, content: str,
                            intent: Optional[str] = None, entities: Optional[List[Dict]] = None):
        """
        Adiciona mensagem à memória da conversa
        
        Args:
            session_id: ID da sessão
            role: Role da mensagem (user/assistant/system)
            content: Conteúdo da mensagem
            intent: Intenção detectada
            entities: Entidades extraídas
        """
        if session_id in self._memories:
            self._memories[session_id].add_entry(
                role=role,
                content=content,
                intent=intent,
                entities=entities
            )
    
    def get_conversation_context(self, session_id: str, max_tokens: int = 2000) -> List[Dict[str, str]]:
        """
        Obtém contexto da conversa para enviar ao LLM
        
        Args:
            session_id: ID da sessão
            max_tokens: Limite de tokens
            
        Returns:
            List[Dict]: Mensagens formatadas para LLM
        """
        if session_id not in self._memories:
            return []
        
        memory = self._memories[session_id]
        context_window = memory.get_context_window(max_tokens)
        
        messages = []
        for entry in context_window:
            messages.append({
                'role': entry.role,
                'content': entry.content
            })
        
        return messages
    
    def _sync_from_django(self, session_state: SessionState, 
                         memory: ConversationMemory, django_session: UserSession):
        """
        Sincroniza estado e memória a partir do Django
        
        Args:
            session_state: Estado da sessão
            memory: Memória da conversa
            django_session: Sessão do Django
        """
        # Sincroniza questão ativa
        if hasattr(django_session, 'active_question_id') and django_session.active_question_id:
            session_state.start_question(django_session.active_question_id)
        
        # Carrega histórico de mensagens
        messages = ChatMessage.objects.filter(
            session=django_session
        ).order_by('created_at')[:50]  # Últimas 50 mensagens
        
        for msg in messages:
            memory.add_entry(
                role='user' if msg.is_user else 'assistant',
                content=msg.content,
                metadata={
                    'message_id': msg.id,
                    'created_at': msg.created_at.isoformat()
                }
            )
        
        # Sincroniza histórico de questões se disponível
        if hasattr(django_session, 'questions_history'):
            for q_data in django_session.questions_history:
                # Adiciona ao histórico do estado
                # (simplificado - seria necessário converter formato completo)
                pass
    
    def sync_to_django(self, session_id: str):
        """
        Sincroniza estado de volta para o Django
        
        Args:
            session_id: ID da sessão
        """
        if session_id not in self._contexts:
            return
        
        context = self._contexts[session_id]
        if not context.django_session:
            return
        
        django_session = context.django_session
        session_state = context.session_state
        
        # Sincroniza questão ativa
        if session_state.active_question:
            django_session.active_question_id = session_state.active_question.question_id
        else:
            django_session.active_question_id = None
        
        # Salva no banco
        try:
            django_session.save()
        except Exception as e:
            logger.error(f"Erro ao sincronizar com Django: {e}")
    
    def clear_context(self, session_id: str):
        """
        Limpa contexto de uma sessão
        
        Args:
            session_id: ID da sessão
        """
        if session_id in self._contexts:
            del self._contexts[session_id]
        if session_id in self._session_states:
            del self._session_states[session_id]
        if session_id in self._memories:
            del self._memories[session_id]
        
        logger.info(f"Contexto limpo para sessão {session_id}")
    
    def get_all_contexts(self) -> Dict[str, Context]:
        """Retorna todos os contextos ativos"""
        return self._contexts.copy()
    
    def cleanup_old_contexts(self, max_age_hours: int = 24):
        """
        Remove contextos antigos
        
        Args:
            max_age_hours: Idade máxima em horas
        """
        now = datetime.utcnow()
        to_remove = []
        
        for session_id, context in self._contexts.items():
            age = (now - context.session_state.updated_at).total_seconds() / 3600
            if age > max_age_hours:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            self.clear_context(session_id)
        
        if to_remove:
            logger.info(f"Removidos {len(to_remove)} contextos antigos")


# Instância global do gerenciador
context_manager = ContextManager()