"""
Modelos de dados específicos para o sistema de agentes
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentAction(Enum):
    """Ações que um agente pode executar"""
    SEARCH_QUESTION = "search_question"
    PRESENT_QUESTION = "present_question"
    VERIFY_ANSWER = "verify_answer"
    SHOW_EXPLANATION = "show_explanation"
    PROVIDE_REFERENCE = "provide_reference"
    GENERATE_RESPONSE = "generate_response"
    UPDATE_CONTEXT = "update_context"
    REQUEST_CLARIFICATION = "request_clarification"
    ROUTE_TO_AGENT = "route_to_agent"


@dataclass
class AgentRequest:
    """Requisição para um agente processar"""
    message: str
    content: Optional[str] = None  # Fase 2 compatibility - alias for message
    intent: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None  # Fase 2 compatibility
    metadata: Dict[str, Any] = field(default_factory=dict)  # Fase 2 compatibility
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Post-init to handle content/message compatibility."""
        if self.content is None:
            self.content = self.message


@dataclass
class AgentTask:
    """Tarefa a ser executada por um agente"""
    action: AgentAction
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # 0 = normal, negativo = baixa, positivo = alta
    timeout_seconds: int = 30
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def should_retry(self) -> bool:
        """Verifica se deve tentar novamente"""
        return self.retry_count < self.max_retries


@dataclass
class AgentExecutionResult:
    """Resultado da execução de uma tarefa por um agente"""
    task: AgentTask
    success: bool
    result_data: Any = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    agent_name: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QuestionSearchCriteria:
    """Critérios para busca de questões"""
    subject_area: Optional[str] = None
    difficulty: Optional[str] = None
    exam: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    exclude_ids: List[str] = field(default_factory=list)
    limit: int = 5
    min_score: float = 0.7


@dataclass
class QuestionPresentation:
    """Dados para apresentação de uma questão"""
    question_id: str
    formatted_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    presentation_style: str = "standard"  # standard, detailed, minimal
    include_instructions: bool = True


@dataclass
class AnswerVerification:
    """Dados para verificação de resposta"""
    question_id: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    confidence: float  # 0.0 a 1.0
    explanation: Optional[str] = None
    time_spent_seconds: int = 0


@dataclass
class StudyReference:
    """Referência de estudo/material"""
    title: str
    description: str
    url: Optional[str] = None
    content_type: str = "article"  # article, video, book, exercise
    relevance_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentCommunication:
    """Comunicação entre agentes"""
    from_agent: str
    to_agent: str
    message_type: str  # request, response, notification
    content: Any
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def create_response(self, content: Any) -> 'AgentCommunication':
        """Cria uma resposta para esta comunicação"""
        return AgentCommunication(
            from_agent=self.to_agent,
            to_agent=self.from_agent,
            message_type="response",
            content=content,
            correlation_id=self.correlation_id or str(id(self))
        )


@dataclass
class AgentMetrics:
    """Métricas de desempenho de um agente"""
    agent_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    uptime_seconds: int = 0
    
    def record_request(self, success: bool, response_time_ms: int):
        """Registra uma nova requisição"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Atualiza média de tempo de resposta
        if self.total_requests == 1:
            self.average_response_time_ms = float(response_time_ms)
        else:
            # Média móvel
            self.average_response_time_ms = (
                (self.average_response_time_ms * (self.total_requests - 1) + response_time_ms) 
                / self.total_requests
            )
        
        self.last_request_time = datetime.utcnow()
    
    def get_success_rate(self) -> float:
        """Calcula taxa de sucesso"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte métricas para dicionário"""
        return {
            'agent_name': self.agent_name,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.get_success_rate(),
            'average_response_time_ms': self.average_response_time_ms,
            'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None,
            'uptime_seconds': self.uptime_seconds
        }