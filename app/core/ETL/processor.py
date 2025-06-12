import logging
import re
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class QuestionProcessor:
    def clean_text(self, text: str) -> str:
        """Limpa e normaliza texto"""
        if not text:
            return ""

        # Remove múltiplos espaços
        text = re.sub(r'\s+', ' ', text)
        # Remove espaços no início/fim
        text = text.strip()

        return text

    def process_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Processa e limpa uma questão"""
        processed = question.copy()

        # Limpa textos
        if 'statement' in processed:
            processed['statement'] = self.clean_text(processed['statement'])

        if 'statement_html' in processed:
            processed['statement_html'] = self.clean_text(processed['statement_html'])

        # Limpa choices
        if 'choices' in processed:
            for key, value in processed['choices'].items():
                processed['choices'][key] = self.clean_text(value)

        # Adiciona timestamp de processamento
        processed['_processed_at'] = datetime.utcnow().isoformat()

        # Garante que subject_area seja lista
        if isinstance(processed.get('subject_area'), str):
            processed['subject_area'] = [processed['subject_area']]

        return processed

    def process_batch(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processa batch de questões"""
        return [self.process_question(q) for q in questions]
