# app/core/services/search.py
"""
Serviço de busca de questões no Qdrant.

Este módulo implementa a busca híbrida (semântica + filtros) de questões
armazenadas no banco vetorial Qdrant, com ranking multi-critério.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, Range, MatchValue, MatchAny
from sentence_transformers import SentenceTransformer
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    """Filtros disponíveis para busca de questões."""
    exam: Optional[str] = None  # ENEM, Vestibular, etc
    subject_area: Optional[List[str]] = None  # Matemática, Português, etc
    subject_discipline: Optional[str] = None  # Disciplina específica (Português, Inglês, etc)
    specific_topic: Optional[str] = None  # Geometria, Gramática, etc
    difficulty: Optional[str] = None  # Fácil, Médio, Difícil
    year: Optional[int] = None  # Ano da prova
    has_images: Optional[bool] = None  # Com ou sem imagens
    keywords: Optional[List[str]] = None  # Palavras-chave específicas
    exclude_ids: Optional[List[str]] = None  # IDs para excluir (já respondidas)


@dataclass
class SearchResult:
    """Resultado de uma busca de questão."""
    question_id: str
    score: float
    semantic_score: float
    ranking_score: float
    metadata: Dict[str, Any]


class SearchService:
    """Serviço responsável pela busca de questões no Qdrant."""
    
    def __init__(self):
        """Inicializa o serviço de busca."""
        # Cliente Qdrant
        self.qdrant_client = QdrantClient(
            host=getattr(settings, 'QDRANT_HOST', 'localhost'),
            port=getattr(settings, 'QDRANT_PORT', 6333)
        )
        self.collection_name = 'questions'
        
        # Modelo de embedding (mesmo usado no ETL)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Cache para embeddings de queries frequentes
        self.cache_prefix = 'search_embedding:'
        self.cache_timeout = 3600  # 1 hora
        
        logger.info("SearchService inicializado")
    
    def search_questions(
        self, 
        query: str, 
        filters: Optional[SearchFilters] = None,
        limit: int = 10,
        user_id: Optional[int] = None,
        min_score: float = 0.3
    ) -> List[SearchResult]:
        """
        Busca questões usando busca híbrida.
        
        Args:
            query: Texto para busca semântica
            filters: Filtros para aplicar
            limit: Número máximo de resultados
            user_id: ID do usuário (para personalização futura)
            min_score: Score mínimo para considerar um resultado relevante
            
        Returns:
            Lista de resultados ordenados por relevância
        """
        try:
            # 1. Gerar embedding da query
            query_embedding = self._get_query_embedding(query)
            
            # 2. Construir filtros do Qdrant
            qdrant_filter = self._build_qdrant_filter(filters) if filters else None
            
            # 3. Executar busca no Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=qdrant_filter,
                limit=limit * 3,  # Buscar mais para ter margem no ranking e filtragem
                with_payload=True,
                with_vectors=False,
                score_threshold=min_score  # Filtrar por score mínimo
            )
            
            # Log para debug quando não há resultados relevantes
            if not search_results:
                logger.info(f"Nenhum resultado com score >= {min_score} para query: '{query}'")
            
            # 4. Processar e ranquear resultados
            ranked_results = self._rank_results(
                search_results, 
                query, 
                filters,
                user_id
            )
            
            # 5. Filtrar resultados com score muito baixo após ranking
            relevant_results = [r for r in ranked_results if r.semantic_score >= min_score]
            
            if not relevant_results and search_results:
                logger.warning(
                    f"Busca por '{query}' retornou {len(search_results)} resultados, "
                    f"mas nenhum com score >= {min_score}. "
                    f"Maior score: {search_results[0].score:.3f}"
                )
            
            # 6. Retornar top N resultados relevantes
            return relevant_results[:limit]
            
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            return []
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """
        Gera embedding para a query, usando cache quando possível.
        
        Args:
            query: Texto da query
            
        Returns:
            Vetor de embedding
        """
        # Tentar pegar do cache
        cache_key = f"{self.cache_prefix}{hash(query)}"
        cached_embedding = cache.get(cache_key)
        
        if cached_embedding is not None:
            return cached_embedding
        
        # Gerar novo embedding
        embedding = self.embedding_model.encode(query).tolist()
        
        # Salvar no cache
        cache.set(cache_key, embedding, self.cache_timeout)
        
        return embedding
    
    def _build_qdrant_filter(self, filters: SearchFilters) -> Optional[Filter]:
        """
        Constrói o filtro para o Qdrant baseado nos filtros fornecidos.
        
        Args:
            filters: Filtros a aplicar
            
        Returns:
            Objeto Filter do Qdrant ou None
        """
        conditions = []
        
        # Filtro por prova
        if filters.exam:
            conditions.append(
                FieldCondition(
                    key="exam",
                    match=MatchValue(value=filters.exam)
                )
            )
        
        # Filtro por área
        if filters.subject_area:
            conditions.append(
                FieldCondition(
                    key="subject_area",
                    match=MatchAny(any=filters.subject_area)
                )
            )
        
        # Filtro por disciplina específica
        if filters.subject_discipline:
            conditions.append(
                FieldCondition(
                    key="subject_discipline",
                    match=MatchValue(value=filters.subject_discipline)
                )
            )
        
        # Filtro por tópico
        if filters.specific_topic:
            conditions.append(
                FieldCondition(
                    key="specific_topic",
                    match=MatchValue(value=filters.specific_topic)
                )
            )
        
        # Filtro por dificuldade
        if filters.difficulty:
            conditions.append(
                FieldCondition(
                    key="difficulty",
                    match=MatchValue(value=filters.difficulty)
                )
            )
        
        # Filtro por ano
        if filters.year:
            conditions.append(
                FieldCondition(
                    key="year",
                    match=MatchValue(value=filters.year)
                )
            )
        
        # Filtro por imagens
        if filters.has_images is not None:
            conditions.append(
                FieldCondition(
                    key="has_images",
                    match=MatchValue(value=filters.has_images)
                )
            )
        
        # Filtro por keywords
        if filters.keywords:
            conditions.append(
                FieldCondition(
                    key="keywords",
                    match=MatchAny(any=filters.keywords)
                )
            )
        
        # Retornar filtro combinado ou None
        if conditions or filters.exclude_ids:
            must_conditions = conditions if conditions else []
            must_not_conditions = []
            
            # Excluir IDs específicos (questões já respondidas)
            if filters.exclude_ids:
                for question_id in filters.exclude_ids:
                    must_not_conditions.append(
                        FieldCondition(
                            key="question_id",
                            match=MatchValue(value=question_id)
                        )
                    )
            
            # Construir filtro com must e must_not
            if must_not_conditions:
                return Filter(
                    must=must_conditions if must_conditions else None,
                    must_not=must_not_conditions
                )
            else:
                return Filter(must=must_conditions)
        
        return None
    
    def _rank_results(
        self, 
        search_results: List[Any],
        query: str,
        filters: Optional[SearchFilters],
        user_id: Optional[int]
    ) -> List[SearchResult]:
        """
        Aplica ranking multi-critério aos resultados.
        
        Critérios considerados:
        1. Score semântico (similaridade do embedding)
        2. Relevância dos filtros
        3. Diversidade (evitar questões muito similares)
        4. Histórico do usuário (futura implementação)
        
        Args:
            search_results: Resultados brutos do Qdrant
            query: Query original
            filters: Filtros aplicados
            user_id: ID do usuário
            
        Returns:
            Lista de SearchResult ordenada
        """
        ranked_results = []
        
        for result in search_results:
            payload = result.payload
            semantic_score = result.score
            
            # Calcular score de ranking adicional
            ranking_score = self._calculate_ranking_score(
                payload, 
                query, 
                filters,
                user_id
            )
            
            # Score final é uma combinação ponderada
            final_score = (0.7 * semantic_score) + (0.3 * ranking_score)
            
            ranked_results.append(
                SearchResult(
                    question_id=payload['question_id'],
                    score=final_score,
                    semantic_score=semantic_score,
                    ranking_score=ranking_score,
                    metadata=payload
                )
            )
        
        # Ordenar por score final
        ranked_results.sort(key=lambda x: x.score, reverse=True)
        
        # Aplicar diversificação (evitar questões muito similares)
        diversified_results = self._diversify_results(ranked_results)
        
        return diversified_results
    
    def _calculate_ranking_score(
        self,
        metadata: Dict[str, Any],
        query: str,
        filters: Optional[SearchFilters],
        user_id: Optional[int]
    ) -> float:
        """
        Calcula score adicional baseado em critérios não-semânticos.
        
        Args:
            metadata: Metadados da questão
            query: Query original
            filters: Filtros aplicados
            user_id: ID do usuário
            
        Returns:
            Score entre 0 e 1
        """
        score = 0.0
        
        # Boost por match exato de filtros
        if filters:
            if filters.exam and metadata.get('exam') == filters.exam:
                score += 0.2
            
            if filters.difficulty and metadata.get('difficulty') == filters.difficulty:
                score += 0.15
            
            if filters.year and metadata.get('year') == filters.year:
                score += 0.1
        
        # Boost por keywords no query
        query_lower = query.lower()
        keywords = metadata.get('keywords', [])
        for keyword in keywords:
            if keyword.lower() in query_lower:
                score += 0.1
                break
        
        # Penalidade para questões muito antigas (> 5 anos)
        year = metadata.get('year')
        if year and isinstance(year, int):
            current_year = datetime.now().year
            age = current_year - year
            if age > 5:
                score -= 0.05 * min(age - 5, 3)  # Max -0.15
        
        # Futuro: considerar histórico do usuário
        # if user_id:
        #     score += self._get_user_preference_score(user_id, metadata)
        
        # Normalizar score entre 0 e 1
        return max(0.0, min(1.0, score))
    
    def _diversify_results(
        self, 
        results: List[SearchResult],
        diversity_threshold: float = 0.8
    ) -> List[SearchResult]:
        """
        Aplica diversificação para evitar resultados muito similares.
        
        Args:
            results: Resultados ordenados
            diversity_threshold: Threshold de similaridade
            
        Returns:
            Resultados diversificados
        """
        if not results:
            return results
        
        diversified = [results[0]]  # Sempre inclui o primeiro
        
        for candidate in results[1:]:
            # Verificar se é suficientemente diferente dos já selecionados
            is_diverse = True
            
            for selected in diversified:
                # Comparar metadados para determinar similaridade
                if self._are_too_similar(
                    candidate.metadata, 
                    selected.metadata,
                    diversity_threshold
                ):
                    is_diverse = False
                    break
            
            if is_diverse:
                diversified.append(candidate)
        
        return diversified
    
    def _are_too_similar(
        self,
        metadata1: Dict[str, Any],
        metadata2: Dict[str, Any],
        threshold: float
    ) -> bool:
        """
        Verifica se duas questões são muito similares.
        
        Args:
            metadata1: Metadados da primeira questão
            metadata2: Metadados da segunda questão
            threshold: Threshold de similaridade
            
        Returns:
            True se são muito similares
        """
        similarity_score = 0.0
        
        # Mesmo tópico específico
        if metadata1.get('specific_topic') == metadata2.get('specific_topic'):
            similarity_score += 0.4
        
        # Mesma dificuldade
        if metadata1.get('difficulty') == metadata2.get('difficulty'):
            similarity_score += 0.2
        
        # Mesmo ano
        if metadata1.get('year') == metadata2.get('year'):
            similarity_score += 0.2
        
        # Keywords em comum
        keywords1 = set(metadata1.get('keywords', []))
        keywords2 = set(metadata2.get('keywords', []))
        if keywords1 and keywords2:
            overlap = len(keywords1.intersection(keywords2)) / len(keywords1.union(keywords2))
            similarity_score += 0.2 * overlap
        
        return similarity_score >= threshold
    
    def get_similar_questions(
        self,
        question_id: str,
        limit: int = 5
    ) -> List[SearchResult]:
        """
        Busca questões similares a uma questão específica.
        
        Args:
            question_id: ID da questão de referência
            limit: Número de resultados
            
        Returns:
            Questões similares
        """
        try:
            # Primeiro, buscar a questão de referência usando filtro
            # já que não podemos usar o ID diretamente no retrieve
            reference_filter = Filter(
                must=[
                    FieldCondition(
                        key="question_id",
                        match=MatchValue(value=question_id)
                    )
                ]
            )
            
            reference_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=[0.0] * 384,  # Vetor dummy
                query_filter=reference_filter,
                limit=1,
                with_vectors=True,
                with_payload=True
            )
            
            if not reference_results:
                logger.warning(f"Questão {question_id} não encontrada")
                return []
            
            reference = reference_results[0]
            
            # Buscar similares usando o vetor da questão
            similar_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=reference.vector,
                limit=limit + 1,  # +1 porque a própria questão virá
                with_payload=True
            )
            
            # Filtrar a própria questão e converter para SearchResult
            results = []
            for result in similar_results:
                if result.payload['question_id'] != question_id:
                    results.append(
                        SearchResult(
                            question_id=result.payload['question_id'],
                            score=result.score,
                            semantic_score=result.score,
                            ranking_score=0.0,
                            metadata=result.payload
                        )
                    )
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Erro ao buscar questões similares: {e}")
            return []