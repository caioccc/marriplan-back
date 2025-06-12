import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class QuestionValidator:
    REQUIRED_FIELDS = [
        'question_id', 'statement', 'choices',
        'correct_choice', 'subject_area'
    ]

    def validate_question(self, question: Dict[str, Any]) -> bool:
        """Valida se a questão tem todos os campos obrigatórios"""
        for field in self.REQUIRED_FIELDS:
            if field not in question:
                logger.warning(f"Campo obrigatório '{field}' ausente em {question.get('question_id', 'Unknown')}")
                return False

        # Valida choices
        if not isinstance(question['choices'], dict) or len(question['choices']) < 2:
            logger.warning(f"Choices inválidas em {question['question_id']}")
            return False

        return True

    def validate_batch(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Valida e retorna apenas questões válidas"""
        valid_questions = []

        for q in questions:
            if self.validate_question(q):
                valid_questions.append(q)

        logger.info(f"Validadas {len(valid_questions)}/{len(questions)} questões")
        return valid_questions
