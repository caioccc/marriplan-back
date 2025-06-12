"""
Chat Agent para conversas naturais e interações casuais.
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
    - Saudações e cumprimentos
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
        """Processa a requisição de chat."""

        try:
            # Identificar tipo de interação e idioma
            interaction_type, language = self._identify_interaction_type(request)

            # Atualizar contexto da conversa
            self._update_conversation_context(request, language)

            # Gerar resposta baseada no tipo e idioma
            response_content = self._generate_response(interaction_type, language, request)

            # Calcular confiança
            confidence = self._calculate_confidence(interaction_type, request)

            # Sugestões de próximas ações (se habilitado)
            suggestions = []
            if self.config['help_suggestions'] and interaction_type in [MessageTypes.GREETING.value, MessageTypes.HELP.value]:
                suggestions = self._get_helpful_suggestions(language)

            # Metadata da resposta
            metadata = {
                'interaction_type': interaction_type,
                'language': language,
                'suggestions': suggestions,
                'conversation_turn': self._get_conversation_turn(request.session_id)
            }

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

    def _generate_response(self, interaction_type: str, language: str, request: AgentRequest) -> str:
        """Gera resposta baseada no tipo de interação e idioma."""

        # Get localized message
        user_name = self._get_user_name(request)
        system_name = self.config.get('system_name', 'Marriplan')

        response = self.localization.get_message(
            language=language,
            message_type=interaction_type,
            user_name=user_name,
            system_name=system_name,
            language=language
        )

        return response


    def _get_user_name(self, request: AgentRequest) -> str:
        """Obtém nome do usuário se disponível."""

        # TODO: Implementar recuperação do nome do usuário
        return "estudante"

    def _calculate_confidence(self, interaction_type: str, request: AgentRequest) -> float:
        """Calcula confiança na resposta."""

        # Confiança base por tipo de interação
        base_confidence = {
            'greeting': 0.95,
            'farewell': 0.95,
            'help': 0.85,
            'about_system': 0.9,
            'clarification': 0.7,
            'casual': 0.6
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
                # Estilo amigável
                "{time_greeting}! 😊 Como posso ajudar você hoje?",
                "Olá! 👋 Pronto para estudar hoje?",
                "{time_greeting}! Estou aqui para ajudar com seus estudos. Em que posso ser útil?",
                "Oi! 😄 Que bom ver você aqui! Como posso ajudar?",
                "{time_greeting}, {user_name}! 🌟 Vamos estudar juntos hoje?",

                # Estilo entusiasmado
                "Eaí! 🔥 Pronto para arrasar nos estudos hoje?",
                "Opa! 🚀 Chegou a hora de aprender coisas incríveis!",
                "Olá! ⚡ Que energia boa! Vamos estudar com garra hoje?",
                "E aí, jovem! 💪 Bora transformar conhecimento em poder?",
                "Heyyy! 🎯 Preparado para uma sessão épica de estudos?",

                # Estilo acolhedor
                "Seja bem-vindo(a)! 🤗 Estou aqui para tornar seus estudos mais fáceis.",
                "Que prazer ter você aqui! 💝 Como posso apoiar seu aprendizado hoje?",
                "Oi, querido(a)! 🌸 Vamos aprender juntos de forma tranquila?",
                "Olá! 🕊️ Estou aqui para ser seu companheiro de estudos. No que posso ajudar?",

                # Estilo motivacional
                "Olá, futuro(a) expert! 🏆 Pronto para mais um passo rumo ao sucesso?",
                "E aí, campeão(ã)! 🥇 Vamos conquistar mais conhecimento hoje?",
                "Oi! 💎 Cada pergunta sua é um investimento no seu futuro brilhante!",
                "Saudações, estudante dedicado(a)! 🌟 Vamos brilhar juntos?"
            ],

            'farewell': [
                # Despedidas motivacionais
                "Até logo! 👋 Continue estudando e boa sorte!",
                "Tchau! 😊 Espero ter ajudado. Volte sempre!",
                "Obrigado por usar o {system_name}! 🎓 Até a próxima!",
                "Adeus! 🌟 Continue se dedicando aos estudos!",
                "Até mais! 📚 Sucesso nos seus estudos!",

                # Despedidas encorajadoras
                "Vai com tudo! 🚀 Você está no caminho certo!",
                "Até a próxima! 💪 Lembre-se: cada estudo conta!",
                "Tchau! 🎯 Confio no seu potencial, continue assim!",
                "Até logo! ⭐ Você está construindo um futuro incrível!",
                "Adeus! 🔥 Mantenha essa dedicação que você vai longe!",

                # Despedidas carinhosas
                "Até breve! 💕 Foi um prazer estudar com você!",
                "Tchau, querido(a)! 🌺 Cuide-se e estude com carinho!",
                "Até logo! 🤗 Lembre-se: eu sempre estarei aqui para ajudar!",
                "Adeus! 🌙 Que seus sonhos sejam repletos de conhecimento!"
            ],

            'help': [
                # Ajuda detalhada
                "Claro! 😊 Estou aqui para ajudar com seus estudos. Posso:\n• Explicar conceitos\n• Fornecer questões para praticar\n• Buscar materiais de estudo\n• Dar dicas de estudo\n\nO que você gostaria de fazer?",
                "Com certeza! 🤝 Sou seu assistente de estudos. Posso ajudar com explicações, questões, referências e muito mais. Do que você precisa?",
                "Estou aqui para isso! 📚 Posso explicar conceitos, criar questões, encontrar materiais... Conte-me o que você quer estudar!",
                "Vamos lá! 🚀 Posso ajudar com várias coisas: tirar dúvidas, praticar com questões, encontrar referências... O que você tem em mente?",

                # Ajuda interativa
                "Perfeito! 🎯 Sou especialista em:\n\n📖 Explicações claras e didáticas\n🧩 Questões personalizadas\n🔍 Busca de materiais específicos\n💡 Dicas de estudo eficazes\n🎓 Preparação para provas\n\nQual dessas opções te interessa mais?",
                "Adoraria ajudar! 💫 Posso ser seu:\n\n🤖 Tutor particular\n📚 Biblioteca pessoal\n🎯 Treinador de questões\n💭 Consultor de estudos\n\nComo prefere que eu te apoie hoje?",
                "Maravilha! 🌟 Tenho superpoderes em:\n\n⚡ Explicações que fazem 'clicar'\n🎲 Questões desafiadoras\n🔮 Materiais sob medida\n🚀 Estratégias de estudo\n\nQual superpower você quer testar primeiro?",

                # Ajuda encorajadora
                "Que ótimo! 💪 Estou aqui para ser seu parceiro de estudos. Juntos, vamos transformar suas dúvidas em conhecimento sólido! Por onde começamos?",
                "Claro que sim! 🌈 Todo grande aprendizado começa com uma pergunta. Estou pronto para te acompanhar nessa jornada. O que você quer descobrir?",
                "Sempre! 🤗 Adoro ajudar estudantes dedicados como você. Vamos fazer deste momento uma experiência de aprendizado incrível! Qual seu desafio?"
            ],

            'about_system': [
                # Apresentação técnica
                "Sou o assistente do {system_name}! 🤖 Estou aqui para tornar seus estudos mais eficientes. Posso:\n\n📖 Explicar conceitos difíceis\n❓ Criar questões personalizadas\n🔍 Encontrar materiais de estudo\n📚 Dar referências confiáveis\n\nExperimente me fazer uma pergunta sobre alguma matéria!",
                "Olá! 👋 Sou seu assistente de estudos inteligente. Uso IA para:\n\n• Responder suas dúvidas\n• Gerar questões adaptadas ao seu nível\n• Buscar os melhores materiais\n• Acompanhar seu progresso\n\nQual matéria você gostaria de estudar?",
                "Sou parte do {system_name}! 🎓 Minha missão é ajudar você a aprender melhor através de:\n\n✨ Explicações personalizadas\n🎯 Questões focadas no que você precisa\n📊 Acompanhamento do seu desenvolvimento\n\nVamos começar? Sobre o que você quer aprender?",

                # Apresentação criativa
                "Olá! 🎭 Sou como um bibliotecário superinteligente, um professor particular 24/7 e um amigo que nunca se cansa de explicar! Posso te ajudar com qualquer matéria. Que tal me testar?",
                "Oi! 🦸‍♂️ Sou o super-herói dos estudos! Meus poderes incluem explicações cristalinas, questões desafiadoras e a habilidade de encontrar exatamente o que você precisa aprender. Qual missão me confia?",
                "E aí! 🎪 Imagine ter acesso a uma biblioteca infinita, um professor genial e um colega de estudos super paciente - tudo em um só lugar! Esse sou eu! Sobre o que você quer conversar?",

                # Apresentação acolhedora
                "Oi! 🌟 Sou como aquele amigo que sempre sabe explicar as coisas de um jeito que faz sentido. Estou aqui para tornar seus estudos mais leves e eficazes. Em que posso te apoiar?",
                "Olá! 🤗 Pense em mim como seu mentor digital - sempre disponível, sempre paciente, sempre com a resposta certa na ponta da língua. Como posso iluminar seu caminho hoje?",
                "Oi, querido(a)! 💝 Sou seu companheiro de jornada no mundo do conhecimento. Estou aqui para transformar cada dúvida em descoberta e cada desafio em conquista. Vamos começar?"
            ],

            'clarification': [
                # Esclarecimentos empáticos
                "Entendo! 🤔 Deixe-me esclarecer isso para você. Sobre qual parte específica você tem dúvidas?",
                "Sem problemas! 😊 Vou explicar de forma mais clara. O que exatamente não ficou claro?",
                "Claro! 💡 Posso explicar melhor. Qual ponto específico você gostaria que eu detalhe mais?",
                "Compreendo sua dúvida! 🧐 Vamos por partes. Qual aspecto você gostaria que eu explique primeiro?",

                # Esclarecimentos didáticos
                "Ótima pergunta! 🎯 Vamos quebrar isso em pedaços menores. Qual parte te confundiu mais?",
                "Perfeito! 📝 Adoro esclarecer conceitos. Vou explicar passo a passo. Por onde você quer que eu comece?",
                "Que bom que perguntou! 🌟 Não há dúvida boba - toda pergunta é uma oportunidade de aprender. O que não ficou claro?",

                # Esclarecimentos encorajadores
                "Isso mesmo! 💪 Fazer perguntas é sinal de inteligência. Vou explicar de um jeito que vai fazer total sentido. Qual sua dúvida específica?",
                "Maravilha! 🚀 Questionar é o primeiro passo para dominar qualquer assunto. Vamos esclarecer isso juntos! Onde você travou?",
                "Excelente! 🏆 Só aprende quem tem coragem de perguntar. Vou explicar quantas vezes for preciso. O que você quer entender melhor?"
            ],

            'casual': [
                # Casuais amigáveis
                "Interessante! 😊 Posso ajudar você com alguma coisa relacionada aos estudos?",
                "Legal! 👍 Já que estamos conversando, que tal aprendermos algo novo hoje?",
                "Entendi! 😄 Aproveitando que você está aqui, posso ajudar com algum tópico de estudo?",
                "Bacana! 🌟 Se quiser, posso sugerir algumas atividades de estudo interessantes!",
                "Ah, entendo! 💭 Já pensou em usar este tempo para revisar alguma matéria?",

                # Casuais descontraídos
                "Opa! 😎 Que tal transformar essa conversa em uma sessão de aprendizado?",
                "Eaí! 🤙 Aproveitando o papo, posso te ensinar algo legal?",
                "Show! 🎵 Que tal misturar diversão com conhecimento?",
                "Massa! 🔥 Posso compartilhar algo interessante com você?",
                "Irado! ⚡ Vamos aproveitar e aprender algo novo juntos?",

                # Casuais curiosos
                "Hmm, interessante! 🕵️‍♀️ Isso me lembra de alguns conceitos fascinantes. Quer conhecer?",
                "Que curioso! 🤓 Isso conecta com várias coisas que posso te mostrar. Tem interesse?",
                "Nossa! 🌍 Isso abre um mundo de possibilidades de aprendizado. Quer explorar?",
                "Caramba! 🎭 Você tocou em um assunto que tem muito pano pra manga. Quer saber mais?",

                # Casuais motivacionais
                "Boa! 🎯 Toda conversa pode virar uma oportunidade de crescer. Que tal aprendermos algo juntos?",
                "Demais! 🚀 Seu interesse me inspira! Posso te ajudar a descobrir coisas incríveis?",
                "Sensacional! 💎 Vejo potencial para transformar essa curiosidade em conhecimento. Topa?",
                "Fantástico! 🌈 Adoro quando encontro alguém aberto a aprender. O que desperta sua curiosidade?"
            ],

            'encouragement': [
                # Novo tipo: encorajamento
                "Você está indo muito bem! 🌟 Continue assim que o sucesso é inevitável!",
                "Que progresso incrível! 💪 Estou orgulhoso da sua dedicação!",
                "Excelente! 🏆 Cada passo seu é uma vitória que merece ser celebrada!",
                "Parabéns! 🎉 Sua persistência é inspiradora!",
                "Fantástico! ⚡ Você está provando que dedicação sempre vale a pena!",
                "Maravilhoso! 🦋 Sua evolução é visível e emocionante!",
                "Sensacional! 🎯 Você está construindo um futuro brilhante!"
            ],

            'study_tips': [
                # Novo tipo: dicas de estudo
                "💡 Dica valiosa: Que tal fazer um resumo do que aprendeu hoje? Ajuda muito na fixação!",
                "🎯 Estratégia inteligente: Intercale matérias diferentes - seu cérebro agradece!",
                "⏰ Técnica comprovada: Estude por 25 minutos, descanse 5. É o método Pomodoro!",
                "📚 Segredo de expert: Ensine para alguém o que aprendeu - é a melhor forma de fixar!",
                "🧠 Hack mental: Conecte conceitos novos com coisas que você já sabe!",
                "🌟 Pro tip: Comemore suas pequenas vitórias - elas motivam para as grandes!",
                "🔄 Técnica ninja: Revise o conteúdo após 1 dia, 1 semana e 1 mês!"
            ]
        }

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
            'last_messages': context['messages'][-3:] if context['messages'] else []
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

        logger.info(f"Configuração de personalidade atualizada: {self.config}")

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do agente."""

        total_sessions = len(self.conversation_context)
        total_interactions = sum(
            ctx['interaction_count']
            for ctx in self.conversation_context.values()
        )

        avg_interactions = total_interactions / total_sessions if total_sessions > 0 else 0

        return {
            'total_sessions': total_sessions,
            'total_interactions': total_interactions,
            'average_interactions_per_session': avg_interactions,
            'config': self.config.copy(),
            'capabilities': [cap.value for cap in self.capabilities],
            'priority': self.priority,
            'template_categories': list(self.response_templates.keys()),
            'service_status': 'active'
        }