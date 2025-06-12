"""
Serviço de reranking para melhorar a qualidade dos resultados de busca RAG.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import math
import re

logger = logging.getLogger(__name__)


@dataclass
class RerankingResult:
    """Resultado do reranking de um documento."""
    content: str
    original_score: float
    reranked_score: float
    metadata: Dict[str, Any]
    rank_position: int
    boost_factors: Dict[str, float]


@dataclass
class RerankingContext:
    """Contexto para o reranking."""
    query: str
    user_context: Optional[Dict[str, Any]] = None
    search_intent: Optional[str] = None
    subject_area: Optional[str] = None
    difficulty_level: Optional[str] = None
    session_history: List[str] = None


class RerankingService:
    """
    Serviço de reranking que melhora a qualidade dos resultados de busca
    usando múltiplos fatores de relevância.
    """
    
    def __init__(self):
        """Inicializa o serviço de reranking."""
        logger.info("RerankingService inicializado")
        
        # Pesos dos fatores de reranking
        self.factor_weights = {
            'semantic_similarity': 0.4,
            'keyword_match': 0.2,
            'context_relevance': 0.15,
            'freshness': 0.1,
            'quality_score': 0.1,
            'user_preference': 0.05
        }
        
        # Cache de scores para otimização
        self._score_cache = {}
        
    def rerank_documents(
        self, 
        documents: List[Dict[str, Any]], 
        context: RerankingContext,
        max_results: int = 10
    ) -> List[RerankingResult]:
        """
        Reranqueia documentos baseado no contexto e query.
        
        Args:
            documents: Lista de documentos com scores originais
            context: Contexto para o reranking
            max_results: Número máximo de resultados
            
        Returns:
            Lista de documentos reranqueados
        """
        if not documents:
            return []
            
        logger.info(f"Reranqueando {len(documents)} documentos para query: '{context.query}'")
        
        reranked_results = []
        
        for doc in documents:
            # Calcular fatores de boost
            boost_factors = self._calculate_boost_factors(doc, context)
            
            # Score original (da busca semântica)
            original_score = doc.get('score', 0.0)
            
            # Calcular novo score
            reranked_score = self._calculate_reranked_score(
                original_score, 
                boost_factors
            )
            
            result = RerankingResult(
                content=doc.get('content', ''),
                original_score=original_score,
                reranked_score=reranked_score,
                metadata=doc.get('metadata', {}),
                rank_position=0,  # Será definido após ordenação
                boost_factors=boost_factors
            )
            
            reranked_results.append(result)
        
        # Ordenar por score reranqueado
        reranked_results.sort(key=lambda x: x.reranked_score, reverse=True)
        
        # Definir posições
        for i, result in enumerate(reranked_results):
            result.rank_position = i + 1
        
        # Limitar resultados
        final_results = reranked_results[:max_results]
        
        logger.info(f"Reranking concluído: {len(final_results)} resultados finais")
        
        return final_results
    
    def _calculate_boost_factors(
        self, 
        document: Dict[str, Any], 
        context: RerankingContext
    ) -> Dict[str, float]:
        """Calcula fatores de boost para um documento."""
        
        content = document.get('content', '').lower()
        metadata = document.get('metadata', {})
        query = context.query.lower()
        
        factors = {}
        
        # 1. Similaridade semântica (já vem do score original)
        factors['semantic_similarity'] = 1.0
        
        # 2. Correspondência de palavras-chave
        factors['keyword_match'] = self._calculate_keyword_match(content, query)
        
        # 3. Relevância contextual
        factors['context_relevance'] = self._calculate_context_relevance(
            document, context
        )
        
        # 4. Frescor (para conteúdo datado)
        factors['freshness'] = self._calculate_freshness_score(metadata)
        
        # 5. Score de qualidade do conteúdo
        factors['quality_score'] = self._calculate_quality_score(content)
        
        # 6. Preferência do usuário
        factors['user_preference'] = self._calculate_user_preference(
            document, context
        )
        
        return factors
    
    def _calculate_keyword_match(self, content: str, query: str) -> float:
        """Calcula correspondência de palavras-chave."""
        
        # Tokenizar query e conteúdo
        query_words = set(re.findall(r'\b\w+\b', query))
        content_words = set(re.findall(r'\b\w+\b', content))
        
        if not query_words:
            return 0.0
        
        # Correspondência exata
        exact_matches = len(query_words.intersection(content_words))
        exact_ratio = exact_matches / len(query_words)
        
        # Correspondência parcial (substring)
        partial_matches = 0
        for query_word in query_words:
            if any(query_word in content_word for content_word in content_words):
                partial_matches += 1
        
        partial_ratio = (partial_matches - exact_matches) / len(query_words)
        
        # Score combinado
        keyword_score = exact_ratio + (partial_ratio * 0.5)
        
        return min(keyword_score, 1.0)
    
    def _calculate_context_relevance(
        self, 
        document: Dict[str, Any], 
        context: RerankingContext
    ) -> float:
        """Calcula relevância contextual."""
        
        relevance_score = 0.0
        metadata = document.get('metadata', {})
        
        # Correspondência de área de estudo
        if context.subject_area:
            doc_subject = metadata.get('subject_area', '').lower()
            if context.subject_area.lower() in doc_subject:
                relevance_score += 0.4
        
        # Correspondência de nível de dificuldade
        if context.difficulty_level:
            doc_difficulty = metadata.get('difficulty', '').lower()
            if context.difficulty_level.lower() == doc_difficulty:
                relevance_score += 0.3
        
        # Correspondência de tipo de conteúdo com intenção
        if context.search_intent:
            doc_type = metadata.get('content_type', '').lower()
            intent_type_mapping = {
                'question': ['questao', 'exercicio', 'problema'],
                'explanation': ['explicacao', 'teoria', 'conceito'],
                'example': ['exemplo', 'caso', 'aplicacao']
            }
            
            intent_keywords = intent_type_mapping.get(context.search_intent.lower(), [])
            if any(keyword in doc_type for keyword in intent_keywords):
                relevance_score += 0.3
        
        return min(relevance_score, 1.0)
    
    def _calculate_freshness_score(self, metadata: Dict[str, Any]) -> float:
        """Calcula score de frescor do conteúdo."""
        
        # Para conteúdo educacional, nem sempre mais novo é melhor
        # Damos preferência moderada a conteúdo mais recente
        
        created_date = metadata.get('created_date')
        if not created_date:
            return 0.8  # Score neutro para conteúdo sem data
        
        try:
            if isinstance(created_date, str):
                created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
            
            # Diferença em dias
            days_old = (datetime.now() - created_date).days
            
            # Score decai suavemente ao longo do tempo
            if days_old <= 30:
                return 1.0
            elif days_old <= 365:
                return 0.9
            elif days_old <= 365 * 2:
                return 0.8
            else:
                return 0.7
                
        except Exception:
            return 0.8
    
    def _calculate_quality_score(self, content: str) -> float:
        """Calcula score de qualidade do conteúdo."""
        
        if not content:
            return 0.0
        
        quality_score = 0.0
        
        # Comprimento adequado (nem muito curto, nem muito longo)
        length = len(content)
        if 100 <= length <= 2000:
            quality_score += 0.3
        elif 50 <= length < 100 or 2000 < length <= 5000:
            quality_score += 0.2
        elif length < 50:
            quality_score += 0.1
        
        # Estrutura (presença de formatação)
        if any(marker in content for marker in ['**', '*', '#', '##', '###']):
            quality_score += 0.2
        
        # Presença de exemplos ou código
        if any(marker in content for marker in ['```', 'exemplo:', 'por exemplo']):
            quality_score += 0.2
        
        # Vocabulário técnico apropriado
        technical_terms = ['conceito', 'teoria', 'propriedade', 'característica', 'método']
        if any(term in content.lower() for term in technical_terms):
            quality_score += 0.2
        
        # Ausência de texto muito repetitivo
        words = content.split()
        if len(set(words)) / len(words) > 0.3:  # Diversidade de vocabulário
            quality_score += 0.1
        
        return min(quality_score, 1.0)
    
    def _calculate_user_preference(
        self, 
        document: Dict[str, Any], 
        context: RerankingContext
    ) -> float:
        """Calcula preferência baseada no histórico do usuário."""
        
        if not context.session_history:
            return 0.5  # Score neutro
        
        # Preferência baseada em interações passadas
        preference_score = 0.5
        
        metadata = document.get('metadata', {})
        doc_type = metadata.get('content_type', '').lower()
        doc_subject = metadata.get('subject_area', '').lower()
        
        # Analisar histórico para preferências
        history_text = ' '.join(context.session_history).lower()
        
        # Se o usuário interage muito com um tipo de conteúdo
        type_mentions = history_text.count(doc_type)
        if type_mentions > 0:
            preference_score += min(type_mentions * 0.1, 0.3)
        
        # Se o usuário interage muito com uma área
        subject_mentions = history_text.count(doc_subject)
        if subject_mentions > 0:
            preference_score += min(subject_mentions * 0.1, 0.2)
        
        return min(preference_score, 1.0)
    
    def _calculate_reranked_score(
        self, 
        original_score: float, 
        boost_factors: Dict[str, float]
    ) -> float:
        """Calcula o score final reranqueado."""
        
        # Score base é o score original da busca semântica
        base_score = original_score
        
        # Calcular boost total baseado nos fatores
        total_boost = 0.0
        
        for factor_name, factor_value in boost_factors.items():
            weight = self.factor_weights.get(factor_name, 0.0)
            total_boost += factor_value * weight
        
        # Aplicar boost ao score base
        # Usamos uma função logarítmica para evitar boosts excessivos
        boost_multiplier = 1.0 + (total_boost * 0.5)
        final_score = base_score * boost_multiplier
        
        # Normalizar entre 0 e 1
        return min(final_score, 1.0)
    
    def get_reranking_explanation(self, result: RerankingResult) -> str:
        """Gera explicação do reranking para debugging."""
        
        explanation_parts = [
            f"Score original: {result.original_score:.3f}",
            f"Score reranqueado: {result.reranked_score:.3f}",
            f"Posição: #{result.rank_position}",
            "",
            "Fatores de boost:"
        ]
        
        for factor, value in result.boost_factors.items():
            weight = self.factor_weights.get(factor, 0.0)
            contribution = value * weight
            explanation_parts.append(
                f"  {factor}: {value:.3f} (peso: {weight:.3f}, contribuição: {contribution:.3f})"
            )
        
        return "\n".join(explanation_parts)
    
    def update_factor_weights(self, new_weights: Dict[str, float]):
        """Atualiza os pesos dos fatores de reranking."""
        
        # Validar que os pesos somam aproximadamente 1.0
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.1:
            logger.warning(f"Pesos não somam 1.0: {total_weight}")
        
        self.factor_weights.update(new_weights)
        logger.info(f"Pesos dos fatores atualizados: {self.factor_weights}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do serviço de reranking."""
        
        return {
            'factor_weights': self.factor_weights.copy(),
            'cache_size': len(self._score_cache),
            'service_status': 'active'
        }