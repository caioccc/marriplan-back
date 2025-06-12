import logging
from typing import List

from app.core.ETL.embedder import QuestionEmbedder
from app.core.ETL.extractor import QuestionExtractor
from app.core.ETL.loader import QuestionLoader
from app.core.ETL.processor import QuestionProcessor
from app.core.ETL.validator import QuestionValidator

logger = logging.getLogger(__name__)


class ETLPipeline:
    def __init__(self):
        self.extractor = QuestionExtractor()
        self.validator = QuestionValidator()
        self.processor = QuestionProcessor()
        self.embedder = QuestionEmbedder()
        self.loader = QuestionLoader()

    def check_already_processed(self, question_ids: List[str]) -> List[str]:
        """Retorna IDs que ainda não foram processados"""
        from app.models import QuestionReference

        processed = QuestionReference.objects.filter(
            question_id__in=question_ids,
            is_processed=True
        ).values_list('question_id', flat=True)

        return [qid for qid in question_ids if qid not in processed]

    def run(self, force: bool = False):
        """Executa pipeline completo"""
        logger.info("Iniciando pipeline ETL...")

        # 1. Extract
        all_questions = self.extractor.extract_all_questions()
        logger.info(f"Total de questões extraídas: {len(all_questions)}")

        if not force:
            # Filtra apenas não processadas
            question_ids = [q['question_id'] for q in all_questions]
            unprocessed_ids = self.check_already_processed(question_ids)
            all_questions = [q for q in all_questions if q['question_id'] in unprocessed_ids]
            logger.info(f"Questões a processar: {len(all_questions)}")

        if not all_questions:
            logger.info("Nenhuma questão nova para processar")
            return

        # 2. Validate
        valid_questions = self.validator.validate_batch(all_questions)

        # 3. Process (Clean)
        processed_questions = self.processor.process_batch(valid_questions)

        # 4. Generate Embeddings
        questions_with_embeddings = self.embedder.generate_embeddings(processed_questions)

        # 5. Load
        self.loader.load_to_mongodb(questions_with_embeddings)
        embedding_map = self.loader.load_to_qdrant(questions_with_embeddings)
        self.loader.update_sqlite_references(questions_with_embeddings, embedding_map)

        logger.info("Pipeline ETL concluído com sucesso!")
