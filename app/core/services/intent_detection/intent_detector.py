"""
Detector principal de intenções usando embeddings
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

from .intent_models import Intent, IntentType, IntentEntity
from .intent_embeddings import IntentEmbeddingManager
from .intent_examples import get_all_examples

logger = logging.getLogger(__name__)


class IntentDetector:
    """Detecta intenções do usuário usando similaridade semântica"""
    
    def __init__(self, embedding_manager: Optional[IntentEmbeddingManager] = None, threshold: float = 0.65):
        """
        Inicializa o detector de intenções
        
        Args:
            embedding_manager: Gerenciador de embeddings (cria um novo se None)
            threshold: Limiar mínimo de confiança para detecção
        """
        self.embedding_manager = embedding_manager or IntentEmbeddingManager()
        self.threshold = threshold
        
        # Prepara embeddings dos exemplos
        self._prepare_example_embeddings()
        
        # Padrões regex para extração de entidades
        self._entity_patterns = self._create_entity_patterns()
        
        logger.info(f"IntentDetector inicializado com threshold={threshold}")
    
    def _prepare_example_embeddings(self):
        """Prepara embeddings de todos os exemplos de treinamento"""
        examples = get_all_examples()
        
        # Separa textos e intenções
        self.example_texts = [ex.text for ex in examples]
        self.example_intents = [ex.intent_type for ex in examples]
        self.example_languages = [ex.language for ex in examples]
        
        # Gera embeddings em batch
        logger.info(f"Gerando embeddings para {len(examples)} exemplos...")
        self.example_embeddings = self.embedding_manager.get_embeddings_batch(self.example_texts)
        logger.info("Embeddings de exemplos preparados")
    
    def _create_entity_patterns(self) -> Dict[str, List[Tuple[re.Pattern, str]]]:
        """Cria padrões regex para extração de entidades"""
        return {
            'answer': [
                (re.compile(r'\b(?:alternativa|letra|opção|resposta)\s+([A-Ea-e])\b', re.IGNORECASE), 'direct'),
                (re.compile(r'\b(?:é\s+)?(?:a\s+)?([A-Ea-e])\s*(?:,|\.|\!|\?|$)', re.IGNORECASE), 'simple'),
                (re.compile(r'^([A-Ea-e])$', re.IGNORECASE), 'single'),
            ],
            'difficulty': [
                (re.compile(r'\b(fácil|fáceis|easy|facile?)\b', re.IGNORECASE), 'Fácil'),
                (re.compile(r'\b(médio|média|medium|moyenne?)\b', re.IGNORECASE), 'Médio'),
                (re.compile(r'\b(difícil|difíceis|hard|difficult|difficile?)\b', re.IGNORECASE), 'Difícil'),
            ],
            'subject_area': [
                # Português/Portuguese
                (re.compile(r'\b(português|portugues|portuguese|portugués)\b', re.IGNORECASE), 'português'),
                # Matemática/Math
                (re.compile(r'\b(matemática|matematica|math|mathematics|matemáticas)\b', re.IGNORECASE), 'matemática'),
                # Geografia/Geography
                (re.compile(r'\b(geografia|geography|géographie|geografía)\b', re.IGNORECASE), 'geografia'),
                # História/History
                (re.compile(r'\b(história|historia|history|histoire)\b', re.IGNORECASE), 'história'),
                # Física/Physics
                (re.compile(r'\b(física|fisica|physics|physique)\b', re.IGNORECASE), 'física'),
                # Química/Chemistry
                (re.compile(r'\b(química|quimica|chemistry|chimie)\b', re.IGNORECASE), 'química'),
                # Biologia/Biology
                (re.compile(r'\b(biologia|biology|biologie|biología)\b', re.IGNORECASE), 'biologia'),
                # Inglês/English
                (re.compile(r'\b(inglês|ingles|english|anglais)\b', re.IGNORECASE), 'inglês'),
                # Espanhol/Spanish
                (re.compile(r'\b(espanhol|spanish|espagnol|español)\b', re.IGNORECASE), 'espanhol'),
            ],
            'exam': [
                (re.compile(r'\b(ENEM|enem)\b', re.IGNORECASE), 'ENEM'),
                (re.compile(r'\b(vestibular)\b', re.IGNORECASE), 'Vestibular'),
                (re.compile(r'\b(concurso)\b', re.IGNORECASE), 'Concurso'),
            ]
        }
    
    def detect(self, text: str, context: Optional[Dict] = None) -> Intent:
        """
        Detecta a intenção de um texto
        
        Args:
            text: Texto do usuário
            context: Contexto adicional (sessão, histórico, etc)
            
        Returns:
            Intent: Intenção detectada com confiança e entidades
        """
        # Gera embedding do texto
        text_embedding = self.embedding_manager.get_embedding(text)
        
        # Encontra exemplos mais similares
        similarities = self.embedding_manager.find_most_similar(
            text_embedding, 
            self.example_embeddings,
            top_k=5
        )
        
        # Analisa resultados
        intent_scores = {}
        for idx, similarity in similarities:
            intent = self.example_intents[idx]
            if intent not in intent_scores or similarity > intent_scores[intent]:
                intent_scores[intent] = similarity
        
        # Seleciona intenção com maior score
        if intent_scores:
            best_intent = max(intent_scores.items(), key=lambda x: x[1])
            intent_type = best_intent[0]
            confidence = best_intent[1]
        else:
            intent_type = IntentType.UNKNOWN
            confidence = 0.0
        
        # Ajusta baseado no contexto
        if context:
            intent_type, confidence = self._adjust_by_context(text, intent_type, confidence, context)
        
        # Se confiança muito baixa, marca como desconhecido
        if confidence < self.threshold:
            intent_type = IntentType.UNKNOWN
        
        # Extrai entidades
        entities = self._extract_entities(text, intent_type)
        
        # Detecta idioma
        language = self._detect_language(text, similarities)
        
        return Intent(
            type=intent_type,
            confidence=float(confidence),
            entities=entities,
            raw_text=text,
            language=language,
            metadata={
                'top_similarities': [(self.example_intents[idx].value, float(sim)) 
                                   for idx, sim in similarities[:3]]
            }
        )
    
    def _adjust_by_context(self, text: str, intent_type: IntentType, 
                          confidence: float, context: Dict) -> Tuple[IntentType, float]:
        """
        Ajusta a detecção baseado no contexto
        
        Args:
            text: Texto original
            intent_type: Tipo detectado
            confidence: Confiança atual
            context: Contexto da sessão
            
        Returns:
            Tuple[IntentType, float]: Tipo e confiança ajustados
        """
        # Se há questão ativa e texto parece resposta
        if context.get('active_question_id'):
            # Verifica se parece uma resposta
            answer_patterns = [
                r'\b[A-Ea-e]\b',
                r'alternativa',
                r'letra',
                r'resposta',
                r'opção'
            ]
            
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in answer_patterns):
                # Aumenta confiança para resposta
                if intent_type == IntentType.ANSWER_QUESTION:
                    confidence = min(confidence * 1.3, 1.0)
                else:
                    # Pode ser resposta mesmo com baixa similaridade
                    intent_type = IntentType.ANSWER_QUESTION
                    confidence = max(confidence, 0.7)
        
        # Se acabou de responder, pedidos genéricos podem ser sobre explicação
        if context.get('last_action') == 'answered_question':
            if intent_type == IntentType.GENERAL_CHAT and confidence < 0.8:
                # Palavras que indicam pedido de explicação
                explanation_words = ['por que', 'porque', 'explica', 'entend', 'detalh']
                if any(word in text.lower() for word in explanation_words):
                    intent_type = IntentType.REQUEST_EXPLANATION
                    confidence = 0.8
        
        return intent_type, confidence
    
    def _extract_entities(self, text: str, intent_type: IntentType) -> List[IntentEntity]:
        """
        Extrai entidades do texto baseado no tipo de intenção
        
        Args:
            text: Texto para extrair entidades
            intent_type: Tipo de intenção detectado
            
        Returns:
            List[IntentEntity]: Entidades extraídas
        """
        entities = []
        
        # Extrai resposta para ANSWER_QUESTION
        if intent_type == IntentType.ANSWER_QUESTION:
            for pattern, pattern_type in self._entity_patterns['answer']:
                match = pattern.search(text)
                if match:
                    answer = match.group(1).upper()
                    entities.append(IntentEntity(
                        entity_type='answer',
                        value=answer,
                        confidence=0.9 if pattern_type == 'direct' else 0.7,
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))
                    break
        
        # Extrai filtros para REQUEST_QUESTION
        elif intent_type == IntentType.REQUEST_QUESTION:
            # Área/disciplina
            for pattern, subject in self._entity_patterns['subject_area']:
                if pattern.search(text):
                    entities.append(IntentEntity(
                        entity_type='subject_area',
                        value=subject,
                        confidence=0.9
                    ))
                    break
            
            # Dificuldade
            for pattern, difficulty in self._entity_patterns['difficulty']:
                if pattern.search(text):
                    entities.append(IntentEntity(
                        entity_type='difficulty',
                        value=difficulty,
                        confidence=0.9
                    ))
                    break
            
            # Prova/exame
            for pattern, exam in self._entity_patterns['exam']:
                if pattern.search(text):
                    entities.append(IntentEntity(
                        entity_type='exam',
                        value=exam,
                        confidence=0.9
                    ))
                    break
        
        return entities
    
    def _detect_language(self, text: str, similarities: List[Tuple[int, float]]) -> str:
        """
        Detecta o idioma baseado nos exemplos mais similares
        
        Args:
            text: Texto original
            similarities: Lista de similaridades com exemplos
            
        Returns:
            str: Código do idioma detectado
        """
        # Conta votos dos top 3 exemplos mais similares
        language_votes = {}
        for idx, _ in similarities[:3]:
            lang = self.example_languages[idx]
            language_votes[lang] = language_votes.get(lang, 0) + 1
        
        # Retorna o idioma mais votado
        if language_votes:
            return max(language_votes.items(), key=lambda x: x[1])[0]
        
        return 'pt'  # Default para português