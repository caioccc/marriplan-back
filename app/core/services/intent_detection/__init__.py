"""
Sistema de Detecção de Intenção

Detecta a intenção do usuário usando embeddings e similaridade semântica
"""

from .intent_detector import IntentDetector
from .intent_models import Intent, IntentType, IntentEntity
from .intent_embeddings import IntentEmbeddingManager

__all__ = [
    'IntentDetector',
    'Intent',
    'IntentType',
    'IntentEntity',
    'IntentEmbeddingManager'
]