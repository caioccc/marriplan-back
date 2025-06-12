"""
RAG (Retrieval-Augmented Generation) Agent para busca e recuperação de informações.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import asyncio
from datetime import datetime

from app.core.agents.base import BaseAgent, AgentResponse, AgentCapability
from app.core.models.agent_models import AgentRequest
from app.core.services.intent_detection import IntentType
from app.core.services.search import SearchService
from app.core.services.reranking import RerankingService, RerankingContext

# Import LLM functionality for advanced synthesis
try:
    from llama_index.core.llms import ChatMessage, MessageRole
    from llama_index.core import Settings
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logger.warning("LLM libraries not available - using basic synthesis")

logger = logging.getLogger(__name__)


class RAGAgent(BaseAgent):
    """
    Agent especializado em Retrieval-Augmented Generation (RAG).
    
    Responsável por:
    - Busca semântica de informações
    - Reranking de resultados
    - Contextualização de informações
    - Síntese de múltiplas fontes
    - Geração de respostas informativas
    """
    
    def __init__(self):
        """Inicializa o RAG Agent."""
        super().__init__(
            name="RAGAgent",
            capabilities=[
                AgentCapability.RAG_SEARCH,
                AgentCapability.REFERENCE_RETRIEVAL,
                AgentCapability.EXPLANATION_GENERATION,
                AgentCapability.STUDY_RECOMMENDATION
            ],
            priority=85  # Alta prioridade para busca de informações
        )
        
        # Inicializar serviços
        self.search_service = SearchService()
        self.reranking_service = RerankingService()
        
        # Cache de resultados para otimização
        self.result_cache = {}
        
        # Configurações do agente
        self.config = {
            'max_search_results': 20,
            'max_final_results': 5,
            'similarity_threshold': 0.3,
            'cache_ttl': 300,  # 5 minutos
            'enable_reranking': True,
            'enable_synthesis': True,
            'use_llm_synthesis': LLM_AVAILABLE and True,  # Síntese com LLM se disponível
            'llm_synthesis_max_sources': 3,  # Máximo de fontes para síntese LLM
            'llm_synthesis_max_length': 800  # Máximo de chars para enviar ao LLM
        }
        
        logger.info("RAG Agent inicializado")
    
    def can_handle(self, request: AgentRequest) -> bool:
        """Verifica se o agente pode processar a requisição."""
        
        # Verificar intent
        intent_data = request.metadata.get('intent', {})
        intent_type = intent_data.get('type', '')
        
        # Intents que o RAG Agent pode processar
        rag_intents = {
            IntentType.REQUEST_EXPLANATION.value,
            IntentType.REQUEST_REFERENCE.value,
            'search_information',
            'explain_concept',
            'find_material',
            'research_topic'
        }
        
        if intent_type in rag_intents:
            return True
        
        # Verificar palavras-chave no conteúdo
        content = request.content or request.message
        rag_keywords = [
            'explicar', 'explicação', 'explique',
            'o que é', 'como funciona', 'definição',
            'material', 'referência', 'fonte',
            'pesquisar', 'buscar', 'encontrar',
            'estudo', 'conceito', 'teoria',
            'informação', 'dados', 'detalhes'
        ]
        
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in rag_keywords):
            return True
        
        return False
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """Processa a requisição RAG."""
        
        try:
            # Extrair informações da requisição
            search_query = self._extract_search_query(request)
            search_context = self._build_search_context(request)
            
            logger.info(f"Processando requisição RAG para: '{search_query}'")
            
            # Verificar cache
            cache_key = self._get_cache_key(search_query, search_context)
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result:
                logger.info("Resultado encontrado no cache")
                return cached_result
            
            # Realizar busca
            search_results = await self._perform_search(search_query, search_context)
            
            if not search_results:
                return AgentResponse(
                    agent_name=self.name,
                    content="Não encontrei informações relevantes sobre o tópico solicitado. Tente reformular sua pergunta ou ser mais específico.",
                    confidence=0.2,
                    metadata={'search_query': search_query, 'results_count': 0}
                )
            
            # Reranking (se habilitado)
            if self.config['enable_reranking']:
                reranked_results = self._rerank_results(search_results, search_context)
            else:
                reranked_results = search_results[:self.config['max_final_results']]
            
            # Síntese das informações (se habilitado)
            if self.config['enable_synthesis']:
                synthesized_content = self._synthesize_information(
                    reranked_results, search_query, search_context
                )
            else:
                synthesized_content = self._format_simple_results(reranked_results)
            
            # Criar resposta
            response = AgentResponse(
                agent_name=self.name,
                content=synthesized_content,
                confidence=self._calculate_confidence(reranked_results),
                metadata={
                    'search_query': search_query,
                    'results_count': len(reranked_results),
                    'sources': [r.metadata for r in reranked_results],
                    'search_context': search_context.__dict__ if hasattr(search_context, '__dict__') else search_context
                }
            )
            
            # Armazenar no cache
            self._cache_result(cache_key, response)
            
            return response
        
        except Exception as e:
            logger.error(f"Erro no processamento RAG: {e}")
            return AgentResponse(
                agent_name=self.name,
                content="Desculpe, ocorreu um erro ao buscar informações. Tente novamente.",
                confidence=0.0,
                metadata={'error': str(e)}
            )
    
    def _extract_search_query(self, request: AgentRequest) -> str:
        """Extrai a query de busca da requisição."""
        
        content = request.content or request.message
        
        # Remover palavras de comando comuns
        stop_words = [
            'explicar', 'explique', 'o que é', 'como funciona',
            'me fale sobre', 'gostaria de saber', 'pode explicar',
            'quero entender', 'preciso saber'
        ]
        
        query = content.lower()
        for stop_word in stop_words:
            query = query.replace(stop_word, '')
        
        # Limpar e retornar
        query = query.strip(' .,?!')
        return query or content
    
    def _build_search_context(self, request: AgentRequest) -> RerankingContext:
        """Constrói contexto para busca e reranking."""
        
        intent_data = request.metadata.get('intent', {})
        entities = intent_data.get('entities', [])
        
        # Extrair entidades relevantes
        subject_area = None
        difficulty_level = None
        
        for entity in entities:
            entity_type = entity.get('entity_type', '').lower()
            entity_value = entity.get('value', '')
            
            if entity_type == 'subject_area':
                subject_area = entity_value
            elif entity_type == 'difficulty':
                difficulty_level = entity_value
        
        # Inferir área de estudo se não especificada
        if not subject_area:
            subject_area = self._infer_subject_area(request.content or request.message)
        
        return RerankingContext(
            query=request.content or request.message,
            user_context=request.metadata,
            search_intent=intent_data.get('type'),
            subject_area=subject_area,
            difficulty_level=difficulty_level,
            session_history=self._get_session_history(request.session_id)
        )
    
    def _infer_subject_area(self, content: str) -> Optional[str]:
        """Infere a área de estudo baseada no conteúdo."""
        
        content_lower = content.lower()
        
        subject_keywords = {
            'Matemática': ['matemática', 'álgebra', 'geometria', 'cálculo', 'equação', 'função', 'integral', 'derivada'],
            'Física': ['física', 'força', 'energia', 'movimento', 'eletricidade', 'magnetismo', 'óptica', 'termodinâmica'],
            'Química': ['química', 'átomo', 'molécula', 'reação', 'elemento', 'composto', 'orgânica', 'inorgânica'],
            'Biologia': ['biologia', 'célula', 'dna', 'evolução', 'ecologia', 'anatomia', 'genética', 'organismo'],
            'História': ['história', 'guerra', 'revolução', 'império', 'república', 'idade média', 'século'],
            'Geografia': ['geografia', 'continente', 'país', 'clima', 'relevo', 'população', 'cidade', 'região'],
            'Português': ['português', 'gramática', 'literatura', 'texto', 'linguagem', 'escrita', 'leitura']
        }
        
        for subject, keywords in subject_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return subject
        
        return None
    
    def _get_session_history(self, session_id: str) -> List[str]:
        """Recupera histórico da sessão para contexto."""
        
        # TODO: Implementar recuperação real do histórico
        # Por ora, retorna lista vazia
        return []
    
    async def _perform_search(
        self, 
        query: str, 
        context: RerankingContext
    ) -> List[Dict[str, Any]]:
        """Realiza a busca semântica."""
        
        try:
            # Preparar parâmetros de busca
            search_params = {
                'query': query,
                'limit': self.config['max_search_results'],
                'score_threshold': self.config['similarity_threshold']
            }
            
            # Adicionar filtros se disponíveis
            if context.subject_area:
                search_params['subject_area'] = context.subject_area
            
            if context.difficulty_level:
                search_params['difficulty'] = context.difficulty_level
            
            # Executar busca
            results = self.search_service.search_documents(**search_params)
            
            logger.info(f"Busca retornou {len(results)} resultados")
            return results
        
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            return []
    
    def _rerank_results(
        self, 
        search_results: List[Dict[str, Any]], 
        context: RerankingContext
    ) -> List:
        """Reranqueia os resultados da busca."""
        
        try:
            reranked = self.reranking_service.rerank_documents(
                search_results, 
                context, 
                max_results=self.config['max_final_results']
            )
            
            logger.info(f"Reranking concluído: {len(reranked)} resultados finais")
            return reranked
        
        except Exception as e:
            logger.error(f"Erro no reranking: {e}")
            return search_results[:self.config['max_final_results']]
    
    def _synthesize_information(
        self, 
        results: List, 
        query: str, 
        context: RerankingContext
    ) -> str:
        """Sintetiza informações de múltiplas fontes usando LLM quando disponível."""
        
        if not results:
            return "Não foram encontradas informações relevantes."
        
        # Verificar se deve usar síntese LLM
        if self.config.get('use_llm_synthesis', False) and LLM_AVAILABLE:
            try:
                synthesized_content = self._create_llm_synthesis(results, query, context)
                if synthesized_content:
                    # Adicionar fontes se habilitado
                    sources_section = self._format_sources(results)
                    if sources_section:
                        return f"{synthesized_content}\n\n{sources_section}"
                    return synthesized_content
            except Exception as e:
                logger.warning(f"Erro na síntese LLM, usando síntese básica: {e}")
        
        # Fallback para síntese básica
        return self._create_basic_synthesis(results, query, context)
    
    def _create_llm_synthesis(
        self, 
        results: List, 
        query: str, 
        context: RerankingContext
    ) -> str:
        """Cria síntese usando LLM para combinar múltiplas fontes de forma inteligente."""
        
        if not LLM_AVAILABLE:
            logger.warning("LLM não disponível para síntese")
            return None
        
        try:
            # Preparar fontes para o LLM
            sources_content = self._prepare_sources_for_llm(results)
            
            # Criar prompt para síntese
            synthesis_prompt = self._build_synthesis_prompt(query, sources_content, context)
            
            # Criar mensagens para o LLM
            messages = [
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content="Você é um assistente educacional especializado em sintetizar informações de múltiplas fontes. "
                           "Sua tarefa é criar uma resposta clara, precisa e bem estruturada que combine as informações "
                           "fornecidas de forma coerente. Use formatação markdown e emojis quando apropriado."
                ),
                ChatMessage(
                    role=MessageRole.USER,
                    content=synthesis_prompt
                )
            ]
            
            # Obter resposta do LLM
            response = Settings.llm.chat(messages)
            synthesized_content = response.message.content.strip()
            
            if synthesized_content:
                logger.info(f"Síntese LLM gerada com sucesso: {len(synthesized_content)} chars")
                return synthesized_content
            else:
                logger.warning("LLM retornou resposta vazia")
                return None
                
        except Exception as e:
            logger.error(f"Erro na síntese LLM: {e}")
            return None
    
    def _prepare_sources_for_llm(self, results: List) -> List[Dict[str, str]]:
        """Prepara fontes para envio ao LLM, limitando tamanho."""
        
        max_sources = self.config.get('llm_synthesis_max_sources', 3)
        max_length = self.config.get('llm_synthesis_max_length', 800)
        
        sources = []
        for i, result in enumerate(results[:max_sources], 1):
            content = result.content if hasattr(result, 'content') else result.get('content', '')
            
            # Limitar tamanho do conteúdo
            if len(content) > max_length:
                content = content[:max_length] + "..."
            
            # Extrair metadados úteis
            metadata = result.metadata if hasattr(result, 'metadata') else result.get('metadata', {})
            source_name = metadata.get('source', f'Fonte {i}')
            subject_area = metadata.get('subject_area', 'Geral')
            
            sources.append({
                'number': i,
                'source': source_name,
                'subject': subject_area,
                'content': content
            })
        
        return sources
    
    def _build_synthesis_prompt(
        self, 
        query: str, 
        sources: List[Dict[str, str]], 
        context: RerankingContext
    ) -> str:
        """Constrói prompt para síntese LLM."""
        
        # Determinar tipo de resposta
        query_lower = query.lower()
        if any(word in query_lower for word in ['o que é', 'definição', 'conceito']):
            response_type = "definição clara e didática"
        elif any(word in query_lower for word in ['como', 'funciona', 'processo']):
            response_type = "explicação do processo passo a passo"
        elif any(word in query_lower for word in ['por que', 'porque', 'motivo']):
            response_type = "explicação das causas e razões"
        else:
            response_type = "resposta informativa e completa"
        
        # Construir prompt
        prompt_parts = [
            f"**Pergunta do usuário:** {query}",
            f"**Tipo de resposta esperada:** {response_type}",
            ""
        ]
        
        # Adicionar contexto se disponível
        if context.subject_area:
            prompt_parts.append(f"**Área de estudo:** {context.subject_area}")
        if context.difficulty_level:
            prompt_parts.append(f"**Nível de dificuldade:** {context.difficulty_level}")
        
        if context.subject_area or context.difficulty_level:
            prompt_parts.append("")
        
        prompt_parts.append("**Fontes de informação:**")
        prompt_parts.append("")
        
        # Adicionar fontes numeradas
        for source in sources:
            prompt_parts.extend([
                f"**Fonte {source['number']} - {source['source']} ({source['subject']}):**",
                source['content'],
                ""
            ])
        
        prompt_parts.extend([
            "**Instruções:**",
            "1. Combine as informações das fontes acima para responder à pergunta",
            "2. Crie uma resposta coerente e bem estruturada",
            "3. Use formatação markdown com títulos e listas quando apropriado",
            "4. Inclua emojis relevantes para tornar a resposta mais amigável",
            "5. Se as fontes apresentarem informações conflitantes, mencione isso",
            "6. Mantenha um tom educacional e didático",
            "7. NÃO mencione 'fonte 1', 'fonte 2', etc. na resposta final",
            "",
            "**Resposta sintetizada:**"
        ])
        
        return "\n".join(prompt_parts)
    
    def _create_basic_synthesis(
        self, 
        results: List, 
        query: str, 
        context: RerankingContext
    ) -> str:
        """Cria síntese básica sem LLM (método original aprimorado)."""
        
        # Cabeçalho da resposta
        response_parts = []
        
        # Determinar tipo de resposta baseado na query
        if any(word in query.lower() for word in ['o que é', 'definição', 'conceito']):
            response_parts.append(f"📖 **Sobre: {query.title()}**\n")
        elif any(word in query.lower() for word in ['como', 'funciona', 'processo']):
            response_parts.append(f"⚙️ **Como funciona: {query.title()}**\n")
        else:
            response_parts.append(f"📚 **Informações sobre: {query.title()}**\n")
        
        # Síntese principal
        main_content = self._create_main_synthesis(results)
        response_parts.append(main_content)
        
        # Pontos-chave se múltiplas fontes
        if len(results) > 1:
            key_points = self._extract_key_points(results)
            if key_points:
                response_parts.append("\n🔍 **Pontos-chave:**")
                for point in key_points:
                    response_parts.append(f"• {point}")
        
        # Fontes
        sources_section = self._format_sources(results)
        if sources_section:
            response_parts.append(f"\n{sources_section}")
        
        return "\n".join(response_parts)
    
    def _create_main_synthesis(self, results: List) -> str:
        """Cria síntese principal do conteúdo (método básico)."""
        
        best_result = results[0]
        content = best_result.content if hasattr(best_result, 'content') else best_result.get('content', '')
        
        # Limitar tamanho se muito longo
        if len(content) > 1000:
            content = content[:1000] + "..."
        
        return content
    
    def _extract_key_points(self, results: List) -> List[str]:
        """Extrai pontos-chave de múltiplas fontes."""
        
        key_points = []
        
        # Extrair frases importantes de cada resultado
        for result in results[:3]:  # Usar apenas top 3
            content = result.content.lower()
            
            # Procurar por frases informativas
            informative_patterns = [
                r'é importante (?:notar|saber|lembrar) que ([^.!?]+)',
                r'(?:deve-se|devemos) (?:considerar|lembrar) que ([^.!?]+)',
                r'(?:característica|propriedade) (?:principal|importante) (?:é|são) ([^.!?]+)',
                r'(?:em resumo|resumindo), ([^.!?]+)'
            ]
            
            import re
            for pattern in informative_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if len(match) > 20 and len(match) < 200:
                        key_points.append(match.strip())
        
        # Remover duplicatas e limitar
        unique_points = list(dict.fromkeys(key_points))
        return unique_points[:3]
    
    def _format_sources(self, results: List) -> str:
        """Formata seção de fontes."""
        
        if not results:
            return ""
        
        sources_parts = ["📖 **Fontes:**"]
        
        for i, result in enumerate(results[:3], 1):
            metadata = result.metadata if hasattr(result, 'metadata') else {}
            
            source_name = metadata.get('source', f'Fonte {i}')
            content_type = metadata.get('content_type', 'documento')
            
            # Score para indicar relevância
            score = result.reranked_score if hasattr(result, 'reranked_score') else result.get('score', 0)
            confidence_icon = "🟢" if score > 0.8 else "🟡" if score > 0.6 else "🔵"
            
            sources_parts.append(f"{confidence_icon} {source_name} ({content_type})")
        
        return "\n".join(sources_parts)
    
    def _format_simple_results(self, results: List) -> str:
        """Formata resultados de forma simples (sem síntese)."""
        
        if not results:
            return "Nenhum resultado encontrado."
        
        response_parts = ["📚 **Resultados encontrados:**\n"]
        
        for i, result in enumerate(results, 1):
            content = result.content if hasattr(result, 'content') else result.get('content', '')
            
            # Limitar tamanho
            if len(content) > 300:
                content = content[:300] + "..."
            
            response_parts.append(f"**{i}.** {content}\n")
        
        return "\n".join(response_parts)
    
    def _calculate_confidence(self, results: List) -> float:
        """Calcula confiança baseada na qualidade dos resultados."""
        
        if not results:
            return 0.0
        
        # Usar score do melhor resultado como base
        best_score = results[0].reranked_score if hasattr(results[0], 'reranked_score') else results[0].get('score', 0)
        
        # Ajustar baseado na quantidade de resultados
        quantity_factor = min(len(results) / 3, 1.0)
        
        # Confiança final
        confidence = best_score * (0.7 + 0.3 * quantity_factor)
        
        return min(confidence, 1.0)
    
    def _get_cache_key(self, query: str, context: RerankingContext) -> str:
        """Gera chave de cache para a requisição."""
        
        key_parts = [
            query.lower().strip(),
            context.subject_area or '',
            context.difficulty_level or '',
            context.search_intent or ''
        ]
        
        return '|'.join(key_parts)
    
    def _get_cached_result(self, cache_key: str) -> Optional[AgentResponse]:
        """Recupera resultado do cache se disponível e válido."""
        
        if cache_key not in self.result_cache:
            return None
        
        cached_entry = self.result_cache[cache_key]
        cached_time = cached_entry['timestamp']
        
        # Verificar se ainda é válido
        if (datetime.now() - cached_time).seconds > self.config['cache_ttl']:
            del self.result_cache[cache_key]
            return None
        
        return cached_entry['response']
    
    def _cache_result(self, cache_key: str, response: AgentResponse):
        """Armazena resultado no cache."""
        
        self.result_cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now()
        }
        
        # Limpar cache se muito grande
        if len(self.result_cache) > 100:
            # Remover entradas mais antigas
            oldest_keys = sorted(
                self.result_cache.keys(),
                key=lambda k: self.result_cache[k]['timestamp']
            )[:20]
            
            for key in oldest_keys:
                del self.result_cache[key]
    
    def update_config(self, new_config: Dict[str, Any]):
        """Atualiza configurações do agente."""
        
        self.config.update(new_config)
        logger.info(f"Configuração do RAG Agent atualizada: {self.config}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do agente."""
        
        return {
            'cache_size': len(self.result_cache),
            'config': self.config.copy(),
            'capabilities': [cap.value for cap in self.capabilities],
            'priority': self.priority,
            'service_status': 'active',
            'llm_available': LLM_AVAILABLE,
            'synthesis_method': 'llm' if (self.config.get('use_llm_synthesis') and LLM_AVAILABLE) else 'basic'
        }
    
    def clear_cache(self):
        """Limpa o cache de resultados."""
        
        self.result_cache.clear()
        logger.info("Cache do RAG Agent limpo")