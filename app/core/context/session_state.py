"""
Gerenciamento do estado da sessão
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionStatus(Enum):
    """Estados possíveis de uma sessão"""
    IDLE = "idle"                               # Aguardando interação
    WAITING_ANSWER = "waiting_answer"           # Aguardando resposta para questão
    PROCESSING = "processing"                   # Processando requisição
    QUESTION_PRESENTED = "question_presented"   # Questão foi apresentada
    ANSWER_GIVEN = "answer_given"              # Resposta foi dada
    EXPLANATION_SHOWN = "explanation_shown"     # Explicação foi mostrada
    ERROR = "error"                            # Erro ocorreu


@dataclass
class QuestionState:
    """Estado de uma questão na sessão"""
    question_id: str
    presented_at: datetime
    answered_at: Optional[datetime] = None
    user_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    explanation_shown: bool = False
    time_spent_seconds: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionState:
    """Estado completo de uma sessão de usuário"""
    session_id: str
    user_id: str
    status: SessionStatus = SessionStatus.IDLE
    active_question: Optional[QuestionState] = None
    questions_history: List[QuestionState] = field(default_factory=list)
    current_intent: Optional[str] = None
    last_action: Optional[str] = None
    last_action_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def set_status(self, status: SessionStatus):
        """Atualiza o status da sessão"""
        self.status = status
        self.updated_at = datetime.utcnow()
    
    def start_question(self, question_id: str) -> QuestionState:
        """Inicia uma nova questão"""
        question = QuestionState(
            question_id=question_id,
            presented_at=datetime.utcnow()
        )
        self.active_question = question
        self.set_status(SessionStatus.QUESTION_PRESENTED)
        self.last_action = "question_presented"
        self.last_action_timestamp = datetime.utcnow()
        return question
    
    def answer_question(self, answer: str, is_correct: bool):
        """Registra resposta para questão ativa"""
        if not self.active_question:
            raise ValueError("Nenhuma questão ativa para responder")
        
        self.active_question.answered_at = datetime.utcnow()
        self.active_question.user_answer = answer
        self.active_question.is_correct = is_correct
        
        # Calcula tempo gasto
        time_diff = self.active_question.answered_at - self.active_question.presented_at
        self.active_question.time_spent_seconds = int(time_diff.total_seconds())
        
        self.set_status(SessionStatus.ANSWER_GIVEN)
        self.last_action = "answered_question"
        self.last_action_timestamp = datetime.utcnow()
    
    def show_explanation(self):
        """Marca que explicação foi mostrada"""
        if self.active_question:
            self.active_question.explanation_shown = True
            self.set_status(SessionStatus.EXPLANATION_SHOWN)
            self.last_action = "showed_explanation"
            self.last_action_timestamp = datetime.utcnow()
    
    def finish_question(self):
        """Finaliza questão ativa e move para histórico"""
        if self.active_question:
            self.questions_history.append(self.active_question)
            self.active_question = None
            self.set_status(SessionStatus.IDLE)
    
    def get_answered_question_ids(self) -> List[str]:
        """Retorna IDs de todas as questões respondidas"""
        ids = []
        
        # Questões no histórico
        for q in self.questions_history:
            if q.user_answer is not None:
                ids.append(q.question_id)
        
        # Questão ativa se respondida
        if self.active_question and self.active_question.user_answer:
            ids.append(self.active_question.question_id)
        
        return ids
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas da sessão"""
        total_questions = len(self.questions_history)
        if self.active_question and self.active_question.user_answer:
            total_questions += 1
        
        correct_answers = sum(1 for q in self.questions_history if q.is_correct)
        if self.active_question and self.active_question.is_correct:
            correct_answers += 1
        
        total_time = sum(q.time_spent_seconds for q in self.questions_history)
        if self.active_question and self.active_question.time_spent_seconds:
            total_time += self.active_question.time_spent_seconds
        
        return {
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'accuracy': correct_answers / total_questions if total_questions > 0 else 0,
            'total_time_seconds': total_time,
            'average_time_seconds': total_time / total_questions if total_questions > 0 else 0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte estado para dicionário"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'status': self.status.value,
            'active_question': self.active_question.__dict__ if self.active_question else None,
            'questions_count': len(self.questions_history),
            'current_intent': self.current_intent,
            'last_action': self.last_action,
            'last_action_timestamp': self.last_action_timestamp.isoformat() if self.last_action_timestamp else None,
            'statistics': self.get_statistics(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }