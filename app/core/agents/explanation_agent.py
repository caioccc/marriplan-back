"""
Explanation Agent - Especializado em fornecer explicações detalhadas e didáticas.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import asyncio
from datetime import datetime
import re

from app.core.agents.base import BaseAgent, AgentResponse, AgentCapability
from app.core.models.agent_models import AgentRequest
from app.core.services.intent_detection import IntentType
from app.core.services.search import SearchService
from app.core.services.reranking import RerankingService, RerankingContext
from app.core.i18n import LocalizationManager, PatternManager, SupportedLanguages, MessageTypes, InteractionPatterns

# Import LLM functionality for advanced explanations
try:
    from llama_index.core.llms import ChatMessage, MessageRole
    from llama_index.core import Settings
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("LLM libraries not available - using basic explanations")

logger = logging.getLogger(__name__)


class ExplanationAgent(BaseAgent):
    """
    Agent especializado em fornecer explicações detalhadas e didáticas.
    
    Responsável por:
    - Explicações conceituais claras e didáticas
    - Demonstrações passo a passo de processos
    - Exemplos práticos e analogias
    - Adaptação ao nível de conhecimento do usuário
    - Sugestões de materiais complementares
    """
    
    def __init__(self):
        """Inicializa o Explanation Agent."""
        super().__init__(
            name="ExplanationAgent",
            capabilities=[
                AgentCapability.EXPLANATION,
                AgentCapability.REFERENCE_RETRIEVAL,
                AgentCapability.CONTENT_GENERATION
            ],
            priority=90  # Alta prioridade para explicações
        )
        
        # Internationalization support
        self.localization = LocalizationManager()
        self.patterns = PatternManager()
        
        # Inicializar serviços
        self.search_service = SearchService()
        self.reranking_service = RerankingService()
        
        # Cache de explicações para otimização
        self.explanation_cache = {}
        
        # Configurações do agente
        self.config = {
            'max_search_results': 15,
            'max_final_results': 5,
            'similarity_threshold': 0.4,
            'cache_ttl': 600,  # 10 minutos
            'enable_reranking': True,
            'use_llm_explanation': LLM_AVAILABLE and True,
            'explanation_depth': 'detailed',  # 'basic', 'detailed', 'advanced'
            'include_examples': True,
            'include_analogies': True,
            'adaptive_complexity': True
        }
        
        logger.info("Explanation Agent inicializado")
    
    def can_handle(self, request: AgentRequest) -> bool:
        """Verifica se o agente pode processar a requisição."""
        
        # Verificar intent
        intent_data = request.metadata.get('intent', {})
        intent_type = intent_data.get('type', '')
        
        # Intents que o Explanation Agent pode processar
        explanation_intents = {
            IntentType.REQUEST_EXPLANATION.value,
            IntentType.REQUEST_HINT.value,
            'concept_explanation',
            'process_explanation',
            'definition'
        }
        
        if intent_type in explanation_intents:
            return True
        
        # Detect language and check patterns
        content = request.content or request.message
        language = self.patterns.detect_language(content)
        
        # Check for explanation patterns
        if self.patterns.check_pattern_match(content, language, InteractionPatterns.EXPLANATION_PATTERN.value):
            return True
        
        # Check for specific explanation keywords
        explanation_keywords = self._get_explanation_keywords(language)
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in explanation_keywords):
            return True
        
        return False
    
    def _get_explanation_keywords(self, language: str) -> List[str]:
        """Obtém palavras-chave de explicação por idioma."""
        
        keywords_by_language = {
            SupportedLanguages.PORTUGUESE.value: [
                'explique', 'o que é', 'como funciona', 'defina', 'conceito',
                'significado', 'ensine', 'demonstre', 'mostre como', 'por que'
            ],
            SupportedLanguages.ENGLISH.value: [
                'explain', 'what is', 'how does', 'define', 'concept',
                'meaning', 'teach', 'demonstrate', 'show how', 'why'
            ],
            SupportedLanguages.SPANISH.value: [
                'explica', 'qué es', 'cómo funciona', 'define', 'concepto',
                'significado', 'enseña', 'demuestra', 'muestra cómo', 'por qué'
            ],
            SupportedLanguages.FRENCH.value: [
                'expliquez', 'qu\'est-ce que', 'comment fonctionne', 'définir', 'concept',
                'signification', 'enseigner', 'démontrer', 'montrer comment', 'pourquoi'
            ]
        }
        
        return keywords_by_language.get(language, keywords_by_language[SupportedLanguages.PORTUGUESE.value])
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """Processa a requisição de explicação."""
        
        try:
            # Detectar idioma
            content = request.content or request.message
            language = self.patterns.detect_language(content)
            
            # Extrair conceito/tópico a ser explicado
            concept = self._extract_concept(content, language)
            
            # Verificar cache
            cache_key = self._get_cache_key(concept, language)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info(f"Explicação recuperada do cache: {concept}")
                return cached_result
            
            # Determinar tipo de explicação necessária
            explanation_type = self._determine_explanation_type(content, language)
            
            # Buscar informações relevantes
            search_results = await self._search_relevant_information(concept, language)
            
            # Reranking dos resultados
            reranked_results = self._rerank_results(search_results, concept, language)
            
            # Gerar explicação
            explanation_content = await self._generate_explanation(
                concept, explanation_type, reranked_results, language
            )
            
            # Calcular confiança
            confidence = self._calculate_confidence(reranked_results, concept)
            
            # Metadata da resposta
            metadata = {
                'concept': concept,
                'explanation_type': explanation_type,
                'language': language,
                'sources_count': len(reranked_results),
                'cache_hit': False
            }
            
            response = AgentResponse(
                agent_name=self.name,
                content=explanation_content,
                confidence=confidence,
                metadata=metadata
            )
            
            # Cache da resposta
            self._cache_result(cache_key, response)
            
            return response
        
        except Exception as e:
            logger.error(f"Erro no processamento da explicação: {e}")
            return AgentResponse(
                agent_name=self.name,
                content=self._get_error_message(language),
                confidence=0.3,
                metadata={'error': str(e), 'language': language}
            )
    
    def _extract_concept(self, content: str, language: str) -> str:
        """Extrai o conceito principal a ser explicado."""
        
        # Remove palavras de interrogação comuns
        remove_patterns = {
            SupportedLanguages.PORTUGUESE.value: [
                r'explique\s+', r'o\s+que\s+é\s+', r'como\s+funciona\s+', r'defina\s+',
                r'conceito\s+de\s+', r'significado\s+de\s+', r'ensine\s+', r'demonstre\s+'
            ],
            SupportedLanguages.ENGLISH.value: [
                r'explain\s+', r'what\s+is\s+', r'how\s+does\s+', r'define\s+',
                r'concept\s+of\s+', r'meaning\s+of\s+', r'teach\s+', r'demonstrate\s+'
            ],
            SupportedLanguages.SPANISH.value: [
                r'explica\s+', r'qué\s+es\s+', r'cómo\s+funciona\s+', r'define\s+',
                r'concepto\s+de\s+', r'significado\s+de\s+', r'enseña\s+', r'demuestra\s+'
            ],
            SupportedLanguages.FRENCH.value: [
                r'expliquez\s+', r'qu\'est-ce\s+que\s+', r'comment\s+fonctionne\s+', r'définir\s+',
                r'concept\s+de\s+', r'signification\s+de\s+', r'enseigner\s+', r'démontrer\s+'
            ]
        }
        
        patterns = remove_patterns.get(language, remove_patterns[SupportedLanguages.PORTUGUESE.value])
        
        concept = content.lower()
        for pattern in patterns:
            concept = re.sub(pattern, '', concept, flags=re.IGNORECASE)
        
        # Remove pontuação e limpa espaços
        concept = re.sub(r'[?!.,:;]', '', concept).strip()
        
        return concept if concept else content
    
    def _determine_explanation_type(self, content: str, language: str) -> str:
        """Determina o tipo de explicação necessária."""
        
        content_lower = content.lower()
        
        type_patterns = {
            'definition': {
                SupportedLanguages.PORTUGUESE.value: ['o que é', 'defina', 'conceito', 'significado'],
                SupportedLanguages.ENGLISH.value: ['what is', 'define', 'concept', 'meaning'],
                SupportedLanguages.SPANISH.value: ['qué es', 'define', 'concepto', 'significado'],
                SupportedLanguages.FRENCH.value: ['qu\'est-ce que', 'définir', 'concept', 'signification']
            },
            'process': {
                SupportedLanguages.PORTUGUESE.value: ['como funciona', 'como fazer', 'processo', 'passo a passo'],
                SupportedLanguages.ENGLISH.value: ['how does', 'how to', 'process', 'step by step'],
                SupportedLanguages.SPANISH.value: ['cómo funciona', 'cómo hacer', 'proceso', 'paso a paso'],
                SupportedLanguages.FRENCH.value: ['comment fonctionne', 'comment faire', 'processus', 'étape par étape']
            },
            'reason': {
                SupportedLanguages.PORTUGUESE.value: ['por que', 'porque', 'motivo', 'razão'],
                SupportedLanguages.ENGLISH.value: ['why', 'because', 'reason', 'cause'],
                SupportedLanguages.SPANISH.value: ['por qué', 'porque', 'motivo', 'razón'],
                SupportedLanguages.FRENCH.value: ['pourquoi', 'parce que', 'motif', 'raison']
            },
            'comparison': {
                SupportedLanguages.PORTUGUESE.value: ['diferença', 'comparar', 'versus', 'vs'],
                SupportedLanguages.ENGLISH.value: ['difference', 'compare', 'versus', 'vs'],
                SupportedLanguages.SPANISH.value: ['diferencia', 'comparar', 'versus', 'vs'],
                SupportedLanguages.FRENCH.value: ['différence', 'comparer', 'versus', 'vs']
            }
        }
        
        for exp_type, patterns in type_patterns.items():
            lang_patterns = patterns.get(language, patterns[SupportedLanguages.PORTUGUESE.value])
            if any(pattern in content_lower for pattern in lang_patterns):
                return exp_type
        
        return 'general'
    
    async def _search_relevant_information(self, concept: str, language: str) -> List:
        """Busca informações relevantes sobre o conceito."""
        
        try:
            # Construir query de busca
            search_query = self._build_search_query(concept, language)
            
            # Realizar busca
            results = self.search_service.search_documents(
                query=search_query,
                limit=self.config['max_search_results'],
                similarity_threshold=self.config['similarity_threshold']
            )
            
            logger.info(f"Busca por '{concept}' retornou {len(results)} resultados")
            return results
        
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            return []
    
    def _build_search_query(self, concept: str, language: str) -> str:
        """Constrói query de busca otimizada."""
        
        # Expandir conceito com sinônimos e termos relacionados
        query_expansions = {
            SupportedLanguages.PORTUGUESE.value: {
                'matemática': ['matemática', 'cálculo', 'álgebra', 'números'],
                'física': ['física', 'mecânica', 'energia', 'força'],
                'química': ['química', 'elementos', 'reações', 'moléculas'],
                'biologia': ['biologia', 'vida', 'organismos', 'células']
            },
            SupportedLanguages.ENGLISH.value: {
                'mathematics': ['mathematics', 'calculus', 'algebra', 'numbers'],
                'physics': ['physics', 'mechanics', 'energy', 'force'],
                'chemistry': ['chemistry', 'elements', 'reactions', 'molecules'],
                'biology': ['biology', 'life', 'organisms', 'cells']
            }
        }
        
        expansions = query_expansions.get(language, {})
        
        # Procurar expansões para o conceito
        concept_lower = concept.lower()
        for key, terms in expansions.items():
            if key in concept_lower:
                return ' '.join(terms)
        
        return concept
    
    def _rerank_results(self, results: List, concept: str, language: str) -> List:
        """Reordena resultados para maximizar relevância educacional."""
        
        if not results or not self.config['enable_reranking']:
            return results[:self.config['max_final_results']]
        
        try:
            # Criar contexto de reranking
            context = RerankingContext(
                query=concept,
                search_intent='explanation',
                difficulty_level='auto_detect',
                subject_area=self._infer_subject_area(concept, language)
            )
            
            # Reranking
            reranked = self.reranking_service.rerank_documents(
                results, 
                context, 
                max_results=self.config['max_final_results']
            )
            
            logger.info(f"Reranking concluído: {len(reranked)} resultados finais")
            return reranked
        
        except Exception as e:
            logger.error(f"Erro no reranking: {e}")
            return results[:self.config['max_final_results']]
    
    def _infer_subject_area(self, concept: str, language: str) -> str:
        """Infere a área de estudo baseada no conceito."""
        
        subject_keywords = {
            SupportedLanguages.PORTUGUESE.value: {
                'Matemática': ['número', 'equação', 'álgebra', 'geometria', 'cálculo', 'função'],
                'Física': ['força', 'energia', 'movimento', 'velocidade', 'massa', 'tempo'],
                'Química': ['elemento', 'molécula', 'reação', 'átomo', 'ligação', 'substância'],
                'Biologia': ['célula', 'organismo', 'vida', 'evolução', 'genética', 'ecologia'],
                'História': ['guerra', 'império', 'revolução', 'época', 'século', 'civilização'],
                'Geografia': ['país', 'continente', 'rio', 'montanha', 'clima', 'população']
            },
            SupportedLanguages.ENGLISH.value: {
                'Mathematics': ['number', 'equation', 'algebra', 'geometry', 'calculus', 'function'],
                'Physics': ['force', 'energy', 'motion', 'velocity', 'mass', 'time'],
                'Chemistry': ['element', 'molecule', 'reaction', 'atom', 'bond', 'substance'],
                'Biology': ['cell', 'organism', 'life', 'evolution', 'genetics', 'ecology'],
                'History': ['war', 'empire', 'revolution', 'era', 'century', 'civilization'],
                'Geography': ['country', 'continent', 'river', 'mountain', 'climate', 'population']
            }
        }
        
        keywords = subject_keywords.get(language, subject_keywords[SupportedLanguages.PORTUGUESE.value])
        concept_lower = concept.lower()
        
        for subject, terms in keywords.items():
            if any(term in concept_lower for term in terms):
                return subject
        
        return 'Geral'
    
    async def _generate_explanation(
        self, 
        concept: str, 
        explanation_type: str, 
        results: List, 
        language: str
    ) -> str:
        """Gera explicação baseada no tipo e resultados."""
        
        if self.config.get('use_llm_explanation', False) and LLM_AVAILABLE:
            try:
                return await self._generate_llm_explanation(concept, explanation_type, results, language)
            except Exception as e:
                logger.warning(f"Erro na explicação LLM, usando explicação básica: {e}")
        
        return self._generate_basic_explanation(concept, explanation_type, results, language)
    
    async def _generate_llm_explanation(
        self, 
        concept: str, 
        explanation_type: str, 
        results: List, 
        language: str
    ) -> str:
        """Gera explicação usando LLM."""
        
        # Preparar contexto dos resultados
        context_info = self._prepare_context_for_llm(results)
        
        # Construir prompt baseado no tipo de explicação
        prompt = self._build_explanation_prompt(concept, explanation_type, context_info, language)
        
        # Criar mensagens para o LLM
        messages = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=self._get_system_prompt(language)
            ),
            ChatMessage(
                role=MessageRole.USER,
                content=prompt
            )
        ]
        
        # Obter resposta do LLM
        response = Settings.llm.chat(messages)
        explanation = response.message.content.strip()
        
        if explanation:
            logger.info(f"Explicação LLM gerada com sucesso: {len(explanation)} chars")
            return explanation
        else:
            logger.warning("LLM retornou explicação vazia")
            return self._generate_basic_explanation(concept, explanation_type, results, language)
    
    def _get_system_prompt(self, language: str) -> str:
        """Obtém prompt de sistema baseado no idioma."""
        
        system_prompts = {
            SupportedLanguages.PORTUGUESE.value: """Você é um tutor educacional especializado em explicações claras e didáticas. 
Sua tarefa é criar explicações que sejam:
- Claras e fáceis de entender
- Adequadas ao nível educacional
- Ricas em exemplos práticos
- Estruturadas de forma lógica
- Motivacionais e envolventes
Use formatação markdown e emojis quando apropriado.""",
            
            SupportedLanguages.ENGLISH.value: """You are an educational tutor specialized in clear and didactic explanations.
Your task is to create explanations that are:
- Clear and easy to understand
- Appropriate for the educational level
- Rich in practical examples
- Logically structured
- Motivational and engaging
Use markdown formatting and emojis when appropriate.""",
            
            SupportedLanguages.SPANISH.value: """Eres un tutor educativo especializado en explicaciones claras y didácticas.
Tu tarea es crear explicaciones que sean:
- Claras y fáciles de entender
- Apropiadas para el nivel educativo
- Ricas en ejemplos prácticos
- Estructuradas de forma lógica
- Motivacionales y atractivas
Usa formato markdown y emojis cuando sea apropiado.""",
            
            SupportedLanguages.FRENCH.value: """Vous êtes un tuteur éducatif spécialisé dans les explications claires et didactiques.
Votre tâche est de créer des explications qui sont:
- Claires et faciles à comprendre
- Appropriées au niveau éducatif
- Riches en exemples pratiques
- Structurées de manière logique
- Motivantes et engageantes
Utilisez le formatage markdown et les emojis quand c'est approprié."""
        }
        
        return system_prompts.get(language, system_prompts[SupportedLanguages.PORTUGUESE.value])
    
    def _build_explanation_prompt(
        self, 
        concept: str, 
        explanation_type: str, 
        context_info: str, 
        language: str
    ) -> str:
        """Constrói prompt para explicação LLM."""
        
        prompt_templates = {
            SupportedLanguages.PORTUGUESE.value: {
                'definition': f"""Explique o conceito de "{concept}" de forma clara e didática.

{context_info}

Estruture sua explicação da seguinte forma:
1. **Definição** - O que é de forma simples
2. **Características principais** - Pontos importantes
3. **Exemplo prático** - Situação do dia a dia
4. **Aplicações** - Onde é usado
5. **Dica de estudo** - Como memorizar/entender melhor

Use emojis e formatação markdown para tornar a explicação mais atrativa.""",

                'process': f"""Explique como funciona "{concept}" de forma passo a passo.

{context_info}

Estruture sua explicação da seguinte forma:
1. **Visão geral** - O que acontece de forma geral
2. **Passo a passo** - Processo detalhado
3. **Exemplo concreto** - Demonstração prática
4. **Pontos importantes** - O que ficar atento
5. **Aplicação prática** - Onde usar esse conhecimento

Use emojis e formatação markdown para facilitar o entendimento.""",

                'reason': f"""Explique por que "{concept}" acontece ou é importante.

{context_info}

Estruture sua explicação da seguinte forma:
1. **Contexto** - Situação ou cenário
2. **Causas** - Por que acontece
3. **Consequências** - O que resulta disso
4. **Importância** - Por que é relevante
5. **Exemplo ilustrativo** - Situação que demonstra

Use emojis e formatação markdown para esclarecer os pontos.""",

                'general': f"""Forneça uma explicação completa sobre "{concept}".

{context_info}

Estruture sua explicação de forma didática e envolvente, incluindo:
- Definição clara
- Características importantes
- Exemplos práticos
- Aplicações relevantes
- Dicas de estudo

Use emojis e formatação markdown para tornar o conteúdo mais atrativo."""
            }
        }
        
        templates = prompt_templates.get(language, prompt_templates[SupportedLanguages.PORTUGUESE.value])
        return templates.get(explanation_type, templates['general'])
    
    def _prepare_context_for_llm(self, results: List) -> str:
        """Prepara contexto dos resultados para o LLM."""
        
        if not results:
            return "**Contexto:** Informações limitadas disponíveis."
        
        context_parts = ["**Contexto baseado nas fontes disponíveis:**\n"]
        
        for i, result in enumerate(results[:3], 1):  # Usar apenas top 3
            content = result.content if hasattr(result, 'content') else result.get('content', '')
            
            # Limitar tamanho
            if len(content) > 400:
                content = content[:400] + "..."
            
            context_parts.append(f"**Fonte {i}:** {content}\n")
        
        return "\n".join(context_parts)
    
    def _generate_basic_explanation(
        self, 
        concept: str, 
        explanation_type: str, 
        results: List, 
        language: str
    ) -> str:
        """Gera explicação básica sem LLM."""
        
        templates = {
            SupportedLanguages.PORTUGUESE.value: {
                'definition': f"📚 **Explicação: {concept.title()}**\n\n",
                'process': f"⚙️ **Como funciona: {concept.title()}**\n\n",
                'reason': f"🤔 **Por que: {concept.title()}**\n\n",
                'general': f"💡 **Sobre: {concept.title()}**\n\n"
            },
            SupportedLanguages.ENGLISH.value: {
                'definition': f"📚 **Explanation: {concept.title()}**\n\n",
                'process': f"⚙️ **How it works: {concept.title()}**\n\n",
                'reason': f"🤔 **Why: {concept.title()}**\n\n",
                'general': f"💡 **About: {concept.title()}**\n\n"
            }
        }
        
        lang_templates = templates.get(language, templates[SupportedLanguages.PORTUGUESE.value])
        header = lang_templates.get(explanation_type, lang_templates['general'])
        
        # Adicionar conteúdo dos resultados
        content_parts = [header]
        
        if results:
            best_result = results[0]
            main_content = best_result.content if hasattr(best_result, 'content') else best_result.get('content', '')
            
            if len(main_content) > 1000:
                main_content = main_content[:1000] + "..."
            
            content_parts.append(main_content)
            
            # Adicionar fontes se múltiplos resultados
            if len(results) > 1:
                sources_text = {
                    SupportedLanguages.PORTUGUESE.value: "\n\n📖 **Fontes adicionais:**",
                    SupportedLanguages.ENGLISH.value: "\n\n📖 **Additional sources:**"
                }.get(language, "\n\n📖 **Fontes adicionais:**")
                
                content_parts.append(sources_text)
                
                for result in results[1:3]:  # Máximo 2 fontes adicionais
                    metadata = result.metadata if hasattr(result, 'metadata') else result.get('metadata', {})
                    source_name = metadata.get('source', 'Fonte')
                    content_parts.append(f"• {source_name}")
        else:
            no_info_text = {
                SupportedLanguages.PORTUGUESE.value: "Não foram encontradas informações específicas sobre este conceito. Tente reformular sua pergunta ou ser mais específico.",
                SupportedLanguages.ENGLISH.value: "No specific information found about this concept. Try rephrasing your question or being more specific."
            }.get(language, "Não foram encontradas informações específicas sobre este conceito.")
            
            content_parts.append(no_info_text)
        
        return "\n".join(content_parts)
    
    def _get_error_message(self, language: str) -> str:
        """Obtém mensagem de erro baseada no idioma."""
        
        error_messages = {
            SupportedLanguages.PORTUGUESE.value: "Desculpe, tive dificuldades para explicar esse conceito. Pode tentar reformular sua pergunta?",
            SupportedLanguages.ENGLISH.value: "Sorry, I had trouble explaining this concept. Could you try rephrasing your question?",
            SupportedLanguages.SPANISH.value: "Disculpa, tuve dificultades para explicar este concepto. ¿Podrías reformular tu pregunta?",
            SupportedLanguages.FRENCH.value: "Désolé, j'ai eu du mal à expliquer ce concept. Pourriez-vous reformuler votre question?"
        }
        
        return error_messages.get(language, error_messages[SupportedLanguages.PORTUGUESE.value])
    
    def _calculate_confidence(self, results: List, concept: str) -> float:
        """Calcula confiança na explicação."""
        
        if not results:
            return 0.3
        
        # Base confidence on result quality
        best_score = results[0].reranked_score if hasattr(results[0], 'reranked_score') else results[0].get('score', 0)
        
        # Adjust based on number of results
        quantity_factor = min(len(results) / 3, 1.0)
        
        # Adjust based on concept complexity (simple heuristic)
        complexity_factor = 1.0
        if len(concept.split()) > 3:
            complexity_factor = 0.9
        
        confidence = best_score * (0.6 + 0.3 * quantity_factor) * complexity_factor
        
        return min(confidence, 0.95)
    
    def _get_cache_key(self, concept: str, language: str) -> str:
        """Gera chave de cache."""
        return f"{concept.lower()}|{language}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[AgentResponse]:
        """Recupera resultado do cache."""
        
        if cache_key not in self.explanation_cache:
            return None
        
        cached_entry = self.explanation_cache[cache_key]
        cached_time = cached_entry['timestamp']
        
        # Verificar se ainda é válido
        if (datetime.now() - cached_time).seconds > self.config['cache_ttl']:
            del self.explanation_cache[cache_key]
            return None
        
        return cached_entry['response']
    
    def _cache_result(self, cache_key: str, response: AgentResponse):
        """Armazena resultado no cache."""
        
        self.explanation_cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now()
        }
        
        # Limitar tamanho do cache
        if len(self.explanation_cache) > 50:
            oldest_keys = sorted(
                self.explanation_cache.keys(),
                key=lambda k: self.explanation_cache[k]['timestamp']
            )[:10]
            
            for key in oldest_keys:
                del self.explanation_cache[key]
    
    def clear_cache(self):
        """Limpa o cache de explicações."""
        self.explanation_cache.clear()
        logger.info("Cache do Explanation Agent limpo")
    
    def update_config(self, new_config: Dict[str, Any]):
        """Atualiza configurações do agente."""
        self.config.update(new_config)
        logger.info(f"Configuração do Explanation Agent atualizada: {self.config}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do agente."""
        
        return {
            'cache_size': len(self.explanation_cache),
            'config': self.config.copy(),
            'capabilities': [cap.value for cap in self.capabilities],
            'priority': self.priority,
            'llm_available': LLM_AVAILABLE,
            'supported_languages': self.localization.get_supported_languages(),
            'service_status': 'active'
        }