# app/core/services/question.py
"""
Serviço para gerenciamento de questões.

Este módulo é responsável por recuperar questões do MongoDB,
formatar para exibição, verificar respostas e gerenciar histórico.
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from dataclasses import dataclass

from pymongo import MongoClient
from django.conf import settings
from django.contrib.auth import get_user_model

from app.models import QuestionReference, UserQuestionHistory

logger = logging.getLogger(__name__)
User = get_user_model()


@dataclass
class QuestionDisplay:
    """Estrutura para exibição de questão formatada."""
    question_id: str
    statement: str
    statement_html: str
    choices: Dict[str, str]
    images: List[Dict[str, Any]]
    subject_area: List[str]
    specific_topic: str
    difficulty: str
    exam: str
    year: Optional[int]


@dataclass
class AnswerResult:
    """Resultado da verificação de resposta."""
    is_correct: bool
    user_answer: str
    correct_answer: str
    explanation: Dict[str, Any]
    time_spent: int  # segundos


class QuestionService:
    """Serviço responsável pelo gerenciamento de questões."""

    def __init__(self):
        """Inicializa o serviço de questões."""
        # Conectar ao MongoDB
        self.mongo_client = MongoClient(
            getattr(settings, 'MONGODB_URL', 'mongodb://localhost:27017/')
        )
        self.mongo_db = self.mongo_client[
            getattr(settings, 'MONGODB_DB', 'marriplan')
        ]
        self.questions_collection = self.mongo_db['questions']

        logger.info("QuestionService inicializado")

    def get_question_by_id(
        self,
        question_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Recupera uma questão completa do MongoDB.

        Args:
            question_id: ID único da questão (SHA1)

        Returns:
            Dict com todos os dados da questão ou None
        """
        try:
            question = self.questions_collection.find_one(
                {'question_id': question_id}
            )

            if not question:
                logger.warning(f"Questão {question_id} não encontrada")
                return None

            # Remover _id do MongoDB para evitar problemas de serialização
            question.pop('_id', None)

            return question

        except Exception as e:
            logger.error(f"Erro ao buscar questão {question_id}: {e}")
            return None

    def format_question_for_display(
        self,
        question_data: Dict[str, Any]
    ) -> QuestionDisplay:
        """
        Formata questão para exibição no chat.

        Args:
            question_data: Dados brutos da questão do MongoDB

        Returns:
            QuestionDisplay com dados formatados
        """
        return QuestionDisplay(
            question_id=question_data['question_id'],
            statement=question_data.get('statement', ''),
            statement_html=question_data.get('statement_html',
                                           question_data.get('statement', '')),
            choices=question_data.get('choices', {}),
            images=question_data.get('images', []),
            subject_area=question_data.get('subject_area', []),
            specific_topic=question_data.get('specific_topic', ''),
            difficulty=question_data.get('difficulty', 'Médio'),
            exam=question_data.get('exam', ''),
            year=question_data.get('year')
        )

    def check_answer(
        self,
        question_id: str,
        user_answer: str,
        user: User,
        session=None,
        time_spent: int = 0
    ) -> Optional[AnswerResult]:
        """
        Verifica se a resposta do usuário está correta.

        Args:
            question_id: ID da questão
            user_answer: Resposta do usuário (A, B, C, D ou E)
            user: Usuário que está respondendo
            time_spent: Tempo gasto em segundos

        Returns:
            AnswerResult com resultado da verificação ou None
        """
        # Normalizar resposta do usuário
        user_answer = user_answer.strip().upper()

        # Validar resposta
        if user_answer not in ['A', 'B', 'C', 'D', 'E']:
            logger.warning(f"Resposta inválida: {user_answer}")
            return None

        # Buscar questão
        question = self.get_question_by_id(question_id)
        if not question:
            return None

        # Verificar resposta
        correct_answer = question.get('correct_choice', '').upper()
        is_correct = user_answer == correct_answer

        # Salvar no histórico se tiver sessão
        if session:
            self._save_to_history(
                session=session,
                question_id=question_id,
                user_answer=user_answer,
                is_correct=is_correct,
                time_spent=time_spent
            )

        # Retornar resultado
        return AnswerResult(
            is_correct=is_correct,
            user_answer=user_answer,
            correct_answer=correct_answer,
            explanation=question.get('explanation', {}),
            time_spent=time_spent
        )

    def _save_to_history(
        self,
        session,
        question_id: str,
        user_answer: str,
        is_correct: bool,
        time_spent: int
    ) -> None:
        """
        Salva resposta no histórico do usuário.

        Args:
            user: Usuário
            question_id: ID da questão
            user_answer: Resposta dada
            is_correct: Se acertou ou não
            time_spent: Tempo gasto
        """
        try:
            # Garantir que existe referência da questão
            question_ref, created = QuestionReference.objects.get_or_create(
                question_id=question_id,
                defaults={
                    'source_file': 'unknown',
                    'is_processed': True
                }
            )

            # Criar registro no histórico
            UserQuestionHistory.objects.create(
                user_session=session,
                question=question_ref,
                user_answer=user_answer,
                is_correct=is_correct,
                time_spent=time_spent
            )

            logger.info(
                f"Histórico salvo: session={session.id}, "
                f"question={question_id}, correct={is_correct}"
            )

        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")

    def get_user_answered_questions(
        self,
        user: User
    ) -> List[str]:
        """
        Retorna IDs das questões já respondidas pelo usuário.

        Args:
            user: Usuário

        Returns:
            Lista de question_ids
        """
        try:
            history = UserQuestionHistory.objects.filter(
                user_session__user=user
            ).values_list('question__question_id', flat=True)

            return list(history)

        except Exception as e:
            logger.error(f"Erro ao buscar histórico: {e}")
            return []

    def get_user_statistics(
        self,
        user: User,
        subject_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retorna estatísticas do usuário.

        Args:
            user: Usuário
            subject_area: Filtrar por área (opcional)

        Returns:
            Dict com estatísticas
        """
        try:
            # Buscar histórico
            history = UserQuestionHistory.objects.filter(user_session__user=user)

            # Filtrar por área se especificado
            if subject_area:
                # Buscar IDs das questões da área
                questions = self.questions_collection.find(
                    {'subject_area': subject_area},
                    {'question_id': 1}
                )
                question_ids = [q['question_id'] for q in questions]

                # Filtrar histórico
                history = history.filter(
                    question__question_id__in=question_ids
                )

            # Calcular estatísticas
            total = history.count()
            correct = history.filter(is_correct=True).count()

            if total == 0:
                accuracy = 0
                avg_time = 0
            else:
                accuracy = (correct / total) * 100
                from django.db import models as django_models
                avg_time = history.aggregate(
                    avg_time=django_models.Avg('time_spent')
                )['avg_time'] or 0

            return {
                'total_answered': total,
                'total_correct': correct,
                'accuracy': round(accuracy, 1),
                'average_time': round(avg_time, 1),
                'subject_area': subject_area
            }

        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {e}")
            return {
                'total_answered': 0,
                'total_correct': 0,
                'accuracy': 0,
                'average_time': 0,
                'subject_area': subject_area
            }

    def format_question_for_chat(
        self,
        question_display: QuestionDisplay
    ) -> str:
        """
        Formata questão para exibição no chat como texto.

        Args:
            question_display: Questão formatada

        Returns:
            String formatada para o chat
        """
        # Cabeçalho
        header = f"📚 **{question_display.exam} - {question_display.subject_area[0]}**\n"
        header += f"📍 Tópico: {question_display.specific_topic}\n"
        header += f"⭐ Dificuldade: {question_display.difficulty}\n\n"

        # Enunciado
        statement = f"**Enunciado:**\n{question_display.statement}\n\n"

        # Alternativas
        choices = "**Alternativas:**\n"
        for letter, text in sorted(question_display.choices.items()):
            choices += f"{letter}) {text}\n"

        # Rodapé
        footer = "\n💡 Digite a letra da alternativa correta (A, B, C, D ou E)"

        return header + statement + choices + footer