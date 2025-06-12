import logging
from typing import List, Dict, Any

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class QuestionEmbedder:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """Inicializa modelo de embeddings"""
        self.model = SentenceTransformer(model_name)
        logger.info(f"Modelo de embeddings '{model_name}' carregado")

    def create_question_text(self, question: Dict[str, Any]) -> str:
        """Cria texto concatenado para embedding"""
        parts = []

        # Adiciona informações da prova
        exam = question.get('exam', '')
        year = question.get('year', '')
        if exam:
            parts.append(f"Prova: {exam}")
        if year:
            parts.append(f"Ano: {year}")

        # Adiciona statement
        parts.append(question.get('statement', ''))

        # Adiciona alternativas (importante para contexto)
        choices = question.get('choices', {})
        if choices:
            for key, value in sorted(choices.items()):
                parts.append(f"{key}) {value}")

        # Adiciona subject areas
        subjects = question.get('subject_area', [])
        if subjects:
            parts.append(f"Matéria: {', '.join(subjects)}")

        # Adiciona topic
        if question.get('specific_topic'):
            parts.append(f"Tópico: {question['specific_topic']}")

        # Adiciona keywords
        keywords = question.get('keywords', [])
        if keywords:
            parts.append(f"Palavras-chave: {', '.join(keywords)}")

        # Adiciona explicação (se disponível)
        explanation = question.get('explanation', {})
        if explanation and explanation.get('text'):
            # Adiciona apenas as primeiras 200 palavras da explicação
            text = explanation['text'][:500] + '...' if len(explanation['text']) > 500 else explanation['text']
            parts.append(f"Contexto: {text}")

        return ' '.join(parts)

    def generate_embeddings(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Gera embeddings para batch de questões"""
        texts = [self.create_question_text(q) for q in questions]

        # Gera embeddings em batch
        embeddings = self.model.encode(texts, convert_to_numpy=True)

        # Adiciona embeddings às questões
        for i, question in enumerate(questions):
            question['_embedding'] = embeddings[i].tolist()

        logger.info(f"Gerados {len(embeddings)} embeddings")
        return questions
