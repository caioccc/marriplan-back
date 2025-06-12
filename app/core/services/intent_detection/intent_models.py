"""
Modelos de dados para o sistema de detecção de intenção
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class IntentType(Enum):
    """Tipos de intenção suportados pelo sistema"""
    # Questões
    REQUEST_QUESTION = "request_question"          # Usuário quer uma questão
    ANSWER_QUESTION = "answer_question"            # Usuário está respondendo
    REQUEST_EXPLANATION = "request_explanation"    # Usuário quer explicação
    REQUEST_HINT = "request_hint"                  # Usuário quer dica
    REQUEST_REFERENCE = "request_reference"        # Usuário quer material de estudo
    
    # Chat geral
    GENERAL_CHAT = "general_chat"                  # Conversa geral
    GREETING = "greeting"                          # Saudação
    FAREWELL = "farewell"                          # Despedida
    
    # Estudo
    REQUEST_STUDY_PLAN = "request_study_plan"      # Plano de estudos
    STUDY_PLAN = "study_plan"                      # Fase 2 compatibility
    REQUEST_PROGRESS = "request_progress"          # Ver progresso
    PROGRESS_CHECK = "progress_check"              # Fase 2 compatibility
    REQUEST_STATISTICS = "request_statistics"      # Ver estatísticas
    SEARCH_CONTENT = "search_content"              # Buscar conteúdo
    
    # Sistema
    HELP = "help"                                  # Ajuda do sistema
    FEEDBACK = "feedback"                          # Feedback do usuário
    UNKNOWN = "unknown"                            # Intenção não identificada


@dataclass
class IntentEntity:
    """Entidade extraída da mensagem do usuário"""
    entity_type: str  # subject_area, difficulty, exam, etc
    value: Any
    confidence: float = 1.0
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Intent:
    """Representação de uma intenção detectada"""
    type: IntentType
    confidence: float  # 0.0 a 1.0
    entities: List[IntentEntity] = field(default_factory=list)
    raw_text: str = ""
    language: str = "pt"  # Idioma detectado
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def get_entity(self, entity_type: str) -> Optional[IntentEntity]:
        """Retorna a primeira entidade do tipo especificado"""
        for entity in self.entities:
            if entity.entity_type == entity_type:
                return entity
        return None
    
    def get_entities_by_type(self, entity_type: str) -> List[IntentEntity]:
        """Retorna todas as entidades do tipo especificado"""
        return [e for e in self.entities if e.entity_type == entity_type]
    
    def has_entity(self, entity_type: str) -> bool:
        """Verifica se possui uma entidade do tipo especificado"""
        return any(e.entity_type == entity_type for e in self.entities)
    
    def is_question_related(self) -> bool:
        """Verifica se a intenção está relacionada a questões"""
        return self.type in [
            IntentType.REQUEST_QUESTION,
            IntentType.ANSWER_QUESTION,
            IntentType.REQUEST_EXPLANATION,
            IntentType.REQUEST_REFERENCE
        ]
    
    def __repr__(self):
        return f"<Intent(type={self.type.value}, confidence={self.confidence:.2f}, entities={len(self.entities)})>"


@dataclass
class IntentExample:
    """Exemplo de treinamento para detecção de intenção"""
    text: str
    intent_type: IntentType
    language: str = "pt"
    entities: List[IntentEntity] = field(default_factory=list)
    
    def __repr__(self):
        return f"<IntentExample(intent={self.intent_type.value}, lang={self.language})>"