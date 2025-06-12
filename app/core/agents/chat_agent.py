"""
Chat Agent para conversas naturais e interações casuais - Versão Internacionalizada.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import re
import random
from datetime import datetime

from app.core.agents.base import BaseAgent, AgentResponse, AgentCapability
from app.core.models.agent_models import AgentRequest
from app.core.services.intent_detection import IntentType
from app.core.i18n import LocalizationManager, PatternManager, SupportedLanguages, MessageTypes, InteractionPatterns

logger = logging.getLogger(__name__)


class ChatAgent(BaseAgent):
    """
    Agent especializado em conversas naturais e interações casuais.

    Responsável por:
    - Saudações e cumprimentos multilíngues
    - Conversas casuais
    - Respostas empáticas
    - Esclarecimentos sobre o sistema
    - Redirecionamento para agentes especializados
    - Manutenção do engajamento do usuário
    """

    def __init__(self):
        """Inicializa o Chat Agent."""
        super().__init__(
            name="ChatAgent",
            capabilities=[
                AgentCapability.CHAT_CONVERSATION,
                AgentCapability.GENERAL_CHAT
            ],
            priority=70  # Prioridade média - outros agentes têm precedência
        )

        # Internationalization support
        self.localization = LocalizationManager()
        self.patterns = PatternManager()

        # Context per session
        self.conversation_context = {}  # Contexto por sessão

        # Configurações
        self.config = {
            'max_conversation_memory': 10,
            'enable_personality': True,
            'response_style': 'friendly',
            'help_suggestions': True,
            'default_language': SupportedLanguages.PORTUGUESE.value,
            'auto_detect_language': True
        }

        logger.info("Chat Agent inicializado com suporte multilíngue")

    def can_handle(self, request: AgentRequest) -> bool:
        """Verifica se o agente pode processar a requisição."""

        # Verificar intent
        intent_data = request.metadata.get('intent', {})
        intent_type = intent_data.get('type', '')

        # Intents que o Chat Agent pode processar
        chat_intents = {
            IntentType.GREETING.value,
            IntentType.GENERAL_CHAT.value,
            'farewell',
            'small_talk',
            'system_help',
            'clarification'
        }

        if intent_type in chat_intents:
            return True

        # Detect language and check patterns
        content = request.content or request.message
        language = self.patterns.detect_language(content)

        # Check for greeting patterns
        if self.patterns.check_pattern_match(content, language, InteractionPatterns.GREETING_PATTERN.value):
            return True

        # Check for farewell patterns
        if self.patterns.check_pattern_match(content, language, InteractionPatterns.FAREWELL_PATTERN.value):
            return True

        # Check for help patterns
        if self.patterns.check_pattern_match(content, language, InteractionPatterns.HELP_PATTERN.value):
            return True

        # Conversa casual (frases curtas sem palavras técnicas)
        if len(content.split()) <= 5 and not self.patterns.contains_technical_terms(content, language):
            return True

        return False

    async def process(self, request: AgentRequest) -> AgentResponse:
        """Processa a requisição de chat, especializado em casamentos."""
        try:
            # Detecta se a pergunta é sobre casamento (simples filtro por palavras-chave)
            wedding_keywords = [
                'casamento', 'noiva', 'noivo', 'festa', 'cerimônia', 'recepção', 'rsvp', 'lista de convidados',
                'fornecedor', 'buffet', 'decoração', 'madrinha', 'padrinho', 'lua de mel', 'aluguel de espaço',
                'convite', 'save the date', 'checklist', 'orçamento', 'cronograma', 'vestido', 'bolo', 'fotógrafo',
                'cerimonial', 'celebração', 'evento', 'casar', 'casamento civil', 'casamento religioso', 'aliança'
            ]
            content_lower = (request.content or request.message or '').lower()
            if not any(word in content_lower for word in wedding_keywords):
                return AgentResponse(
                    agent_name=self.name,
                    content="Desculpe, mas só posso ajudar com dúvidas relacionadas ao planejamento do seu casamento. 😊",
                    confidence=1.0,
                    metadata={'filtered': True}
                )

            # Chama o modelo de IA (aqui, simula a chamada com a função original)
            interaction_type, language = self._identify_interaction_type(request)
            self._update_conversation_context(request, language)
            response_content = self._generate_response(interaction_type, language)
            confidence = self._calculate_confidence(interaction_type, request)
            suggestions = []
            if self.config['help_suggestions'] and interaction_type in [MessageTypes.GREETING.value, MessageTypes.HELP.value]:
                suggestions = self._get_helpful_suggestions(language)
            metadata = {
                'interaction_type': interaction_type,
                'language': language,
                'suggestions': suggestions,
                'conversation_turn': self._get_conversation_turn(request.session_id)
            }

            # Filtragem de resposta: se a resposta não mencionar casamento, retorna aviso
            if not any(word in response_content.lower() for word in wedding_keywords):
                response_content = "Só posso responder dúvidas sobre casamentos. Por favor, pergunte algo relacionado ao tema."
                confidence = 1.0
                metadata['filtered'] = True

            return AgentResponse(
                agent_name=self.name,
                content=response_content,
                confidence=confidence,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Erro no processamento do chat: {e}")
            return AgentResponse(
                agent_name=self.name,
                content="Desculpe, tive um problema para processar sua mensagem. Pode tentar novamente?",
                confidence=0.5,
                metadata={'error': str(e)}
            )

    def _identify_interaction_type(self, request: AgentRequest) -> Tuple[str, str]:
        """Identifica o tipo de interação e detecta o idioma."""

        content = request.content or request.message

        # Detect language first
        language = self.patterns.detect_language(content)

        # Verificar intent primeiro
        intent_data = request.metadata.get('intent', {})
        intent_type = intent_data.get('type', '')

        if intent_type == IntentType.GREETING.value:
            return MessageTypes.GREETING.value, language
        elif intent_type == IntentType.GENERAL_CHAT.value:
            return MessageTypes.CASUAL.value, language

        # Check patterns using detected language
        if self.patterns.check_pattern_match(content, language, InteractionPatterns.GREETING_PATTERN.value):
            return MessageTypes.GREETING.value, language

        if self.patterns.check_pattern_match(content, language, InteractionPatterns.FAREWELL_PATTERN.value):
            return MessageTypes.FAREWELL.value, language

        if self.patterns.check_pattern_match(content, language, InteractionPatterns.HELP_PATTERN.value):
            return MessageTypes.HELP.value, language

        # Check for system-related questions (multilingual)
        system_patterns = {
            SupportedLanguages.PORTUGUESE.value: ['o que você', 'que tipo', 'para que serve'],
            SupportedLanguages.ENGLISH.value: ['what do you', 'what can you', 'what are you'],
            SupportedLanguages.SPANISH.value: ['qué haces', 'qué puedes', 'para qué sirves'],
            SupportedLanguages.FRENCH.value: ['que faites-vous', 'que pouvez-vous', 'à quoi servez']
        }

        content_lower = content.lower()
        for pattern in system_patterns.get(language, []):
            if pattern in content_lower:
                return MessageTypes.ABOUT_SYSTEM.value, language

        # Check for clarification requests
        clarification_patterns = {
            SupportedLanguages.PORTUGUESE.value: ['não entendi', 'confuso', 'esclarecer'],
            SupportedLanguages.ENGLISH.value: ['don\'t understand', 'confused', 'clarify'],
            SupportedLanguages.SPANISH.value: ['no entiendo', 'confundido', 'aclarar'],
            SupportedLanguages.FRENCH.value: ['ne comprends pas', 'confus', 'clarifier']
        }

        for pattern in clarification_patterns.get(language, []):
            if pattern in content_lower:
                return MessageTypes.CLARIFICATION.value, language

        # Default para casual
        return MessageTypes.CASUAL.value, language

    def _generate_response(self, interaction_type: str, language: str) -> str:
        """Gera resposta baseada no tipo de interação e idioma."""
        user_name = self._get_user_name()
        system_name = self.config.get('system_name', 'Marriplan')
        response = self.localization.get_message(
            language=language,
            message_type=interaction_type,
            user_name=user_name,
            system_name=system_name,
            language=language
        )
        return response

    def _get_user_name(self) -> str:
        """Obtém nome do usuário se disponível."""
        return "usuário"

    def _calculate_confidence(self, interaction_type: str, request: AgentRequest) -> float:
        """Calcula confiança na resposta."""

        # Confiança base por tipo de interação
        base_confidence = {
            MessageTypes.GREETING.value: 0.95,
            MessageTypes.FAREWELL.value: 0.95,
            MessageTypes.HELP.value: 0.85,
            MessageTypes.ABOUT_SYSTEM.value: 0.9,
            MessageTypes.CLARIFICATION.value: 0.7,
            MessageTypes.CASUAL.value: 0.6
        }

        confidence = base_confidence.get(interaction_type, 0.5)

        # Ajustar baseado na clareza da mensagem
        content = request.content or request.message
        if len(content.split()) <= 3:  # Mensagens muito curtas
            confidence *= 0.9

        return confidence

    def _get_helpful_suggestions(self, language: str) -> List[str]:
        """Gera sugestões úteis para o usuário baseadas no idioma."""

        suggestions_by_language = {
            SupportedLanguages.PORTUGUESE.value: [
                "💡 Posso ajudar você com questões de estudo",
                "📚 Experimente pedir uma explicação sobre algum conceito",
                "❓ Solicite uma questão de alguma matéria específica",
                "🔍 Busque materiais de estudo sobre um tópico",
                "📖 Peça referências sobre algum assunto"
            ],
            SupportedLanguages.ENGLISH.value: [
                "💡 I can help you with study questions",
                "📚 Try asking for an explanation about some concept",
                "❓ Request a question from a specific subject",
                "🔍 Search for study materials on a topic",
                "📖 Ask for references on some subject"
            ],
            SupportedLanguages.SPANISH.value: [
                "💡 Puedo ayudarte con preguntas de estudio",
                "📚 Intenta pedir una explicación sobre algún concepto",
                "❓ Solicita una pregunta de alguna materia específica",
                "🔍 Busca materiales de estudio sobre un tema",
                "📖 Pide referencias sobre algún tema"
            ],
            SupportedLanguages.FRENCH.value: [
                "💡 Je peux vous aider avec des questions d'étude",
                "📚 Essayez de demander une explication sur un concept",
                "❓ Demandez une question d'une matière spécifique",
                "🔍 Cherchez des matériaux d'étude sur un sujet",
                "📖 Demandez des références sur un sujet"
            ]
        }

        suggestions = suggestions_by_language.get(language, suggestions_by_language[SupportedLanguages.PORTUGUESE.value])

        # Retornar algumas sugestões aleatórias
        return random.sample(suggestions, min(3, len(suggestions)))

    def _update_conversation_context(self, request: AgentRequest, language: str):
        """Atualiza contexto da conversa."""

        session_id = request.session_id

        if session_id not in self.conversation_context:
            self.conversation_context[session_id] = {
                'messages': [],
                'start_time': datetime.now(),
                'interaction_count': 0,
                'primary_language': language,
                'languages_used': set([language])
            }
        else:
            # Update language information
            self.conversation_context[session_id]['languages_used'].add(language)

        context = self.conversation_context[session_id]
        context['messages'].append({
            'content': request.content or request.message,
            'timestamp': datetime.now(),
            'language': language
        })
        context['interaction_count'] += 1

        # Limitar histórico
        max_memory = self.config['max_conversation_memory']
        if len(context['messages']) > max_memory:
            context['messages'] = context['messages'][-max_memory:]

    def _get_conversation_turn(self, session_id: str) -> int:
        """Retorna número do turno da conversa."""

        if session_id in self.conversation_context:
            return self.conversation_context[session_id]['interaction_count']
        return 1

    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Retorna resumo da conversa de uma sessão."""

        if session_id not in self.conversation_context:
            return {'status': 'no_conversation'}

        context = self.conversation_context[session_id]

        return {
            'message_count': len(context['messages']),
            'start_time': context['start_time'].isoformat(),
            'interaction_count': context['interaction_count'],
            'duration_minutes': (datetime.now() - context['start_time']).seconds // 60,
            'last_messages': context['messages'][-3:] if context['messages'] else [],
            'primary_language': context.get('primary_language', SupportedLanguages.PORTUGUESE.value),
            'languages_used': list(context.get('languages_used', set()))
        }

    def clear_conversation_context(self, session_id: str = None):
        """Limpa contexto de conversa."""

        if session_id:
            if session_id in self.conversation_context:
                del self.conversation_context[session_id]
                logger.info(f"Contexto da sessão {session_id} limpo")
        else:
            self.conversation_context.clear()
            logger.info("Todos os contextos de conversa limpos")

    def update_personality_config(self, new_config: Dict[str, Any]):
        """Atualiza configuração de personalidade."""

        valid_styles = ['friendly', 'formal', 'casual', 'enthusiastic']

        if 'response_style' in new_config:
            if new_config['response_style'] in valid_styles:
                self.config['response_style'] = new_config['response_style']

        if 'enable_personality' in new_config:
            self.config['enable_personality'] = bool(new_config['enable_personality'])

        if 'help_suggestions' in new_config:
            self.config['help_suggestions'] = bool(new_config['help_suggestions'])

        if 'default_language' in new_config:
            supported_languages = [lang.value for lang in SupportedLanguages]
            if new_config['default_language'] in supported_languages:
                self.config['default_language'] = new_config['default_language']

        logger.info(f"Configuração de personalidade atualizada: {self.config}")

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do agente."""

        total_sessions = len(self.conversation_context)
        total_interactions = sum(
            ctx['interaction_count']
            for ctx in self.conversation_context.values()
        )

        avg_interactions = total_interactions / total_sessions if total_sessions > 0 else 0

        # Language statistics
        language_usage = {}
        for ctx in self.conversation_context.values():
            primary_lang = ctx.get('primary_language', SupportedLanguages.PORTUGUESE.value)
            language_usage[primary_lang] = language_usage.get(primary_lang, 0) + 1

        return {
            'total_sessions': total_sessions,
            'total_interactions': total_interactions,
            'average_interactions_per_session': avg_interactions,
            'config': self.config.copy(),
            'capabilities': [cap.value for cap in self.capabilities],
            'priority': self.priority,
            'supported_languages': self.localization.get_supported_languages(),
            'language_usage': language_usage,
            'service_status': 'active'
        }