"""
Gerenciador de embeddings para detecção de intenção
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from sentence_transformers import SentenceTransformer
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class IntentEmbeddingManager:
    """Gerencia embeddings para detecção de intenção"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Inicializa o gerenciador de embeddings
        
        Args:
            model_name: Nome do modelo sentence-transformers a usar
        """
        logger.info(f"Inicializando IntentEmbeddingManager com modelo {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        self._cache: Dict[str, np.ndarray] = {}
    
    @lru_cache(maxsize=1000)
    def get_embedding(self, text: str) -> np.ndarray:
        """
        Gera embedding para um texto
        
        Args:
            text: Texto para gerar embedding
            
        Returns:
            np.ndarray: Vetor de embedding
        """
        # Verifica cache primeiro
        cache_key = text.lower().strip()
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Gera novo embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        # Adiciona ao cache
        self._cache[cache_key] = embedding
        
        return embedding
    
    def get_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """
        Gera embeddings para múltiplos textos
        
        Args:
            texts: Lista de textos
            
        Returns:
            np.ndarray: Matriz de embeddings
        """
        # Separa textos já em cache dos novos
        cached_embeddings = []
        new_texts = []
        new_indices = []
        
        for i, text in enumerate(texts):
            cache_key = text.lower().strip()
            if cache_key in self._cache:
                cached_embeddings.append((i, self._cache[cache_key]))
            else:
                new_texts.append(text)
                new_indices.append(i)
        
        # Gera embeddings para textos novos
        if new_texts:
            new_embeddings = self.model.encode(new_texts, convert_to_numpy=True)
            
            # Adiciona ao cache
            for text, embedding in zip(new_texts, new_embeddings):
                cache_key = text.lower().strip()
                self._cache[cache_key] = embedding
        
        # Combina resultados na ordem original
        result = np.zeros((len(texts), self.embedding_dim))
        
        # Adiciona embeddings em cache
        for idx, embedding in cached_embeddings:
            result[idx] = embedding
        
        # Adiciona novos embeddings
        if new_texts:
            for idx, embedding in zip(new_indices, new_embeddings):
                result[idx] = embedding
        
        return result
    
    def cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calcula similaridade de cosseno entre dois embeddings
        
        Args:
            embedding1: Primeiro embedding
            embedding2: Segundo embedding
            
        Returns:
            float: Similaridade entre -1 e 1
        """
        # Normaliza vetores
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Calcula similaridade
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        return float(similarity)
    
    def find_most_similar(self, 
                         query_embedding: np.ndarray, 
                         candidate_embeddings: np.ndarray,
                         top_k: int = 1) -> List[Tuple[int, float]]:
        """
        Encontra os embeddings mais similares
        
        Args:
            query_embedding: Embedding de consulta
            candidate_embeddings: Matriz de embeddings candidatos
            top_k: Número de resultados a retornar
            
        Returns:
            List[Tuple[int, float]]: Lista de (índice, similaridade)
        """
        # Calcula similaridades
        similarities = []
        for i, candidate in enumerate(candidate_embeddings):
            sim = self.cosine_similarity(query_embedding, candidate)
            similarities.append((i, sim))
        
        # Ordena por similaridade
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def clear_cache(self):
        """Limpa o cache de embeddings"""
        self._cache.clear()
        self.get_embedding.cache_clear()
        logger.info("Cache de embeddings limpo")
    
    def cache_size(self) -> int:
        """Retorna o tamanho atual do cache"""
        return len(self._cache)