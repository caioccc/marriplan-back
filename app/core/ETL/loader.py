# app/etl/loader.py
from typing import List, Dict, Any
import logging
from pymongo import MongoClient, UpdateOne
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)


class QuestionLoader:
    def __init__(self):
        # MongoDB
        self.mongo_client = MongoClient(getattr(settings, 'MONGODB_URL', 'mongodb://localhost:27017/'))
        self.mongo_db = self.mongo_client[getattr(settings, 'MONGODB_DB', 'marriplan')]
        self.mongo_collection = self.mongo_db['questions']

        # Qdrant
        self.qdrant_client = QdrantClient(
            host=getattr(settings, 'QDRANT_HOST', 'localhost'),
            port=getattr(settings, 'QDRANT_PORT', 6333)
        )
        self.collection_name = 'questions'
        self._ensure_qdrant_collection()

    def _ensure_qdrant_collection(self):
        """Garante que a collection existe no Qdrant"""
        collections = self.qdrant_client.get_collections().collections

        if not any(c.name == self.collection_name for c in collections):
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info(f"Collection '{self.collection_name}' criada no Qdrant")

    def load_to_mongodb(self, questions: List[Dict[str, Any]]) -> None:
        """Carrega questões no MongoDB (upsert)"""
        operations = []

        for q in questions:
            # Remove embedding antes de salvar no Mongo
            q_copy = q.copy()
            q_copy.pop('_embedding', None)

            operations.append(
                UpdateOne(
                    {'question_id': q['question_id']},
                    {'$set': q_copy},
                    upsert=True
                )
            )

        if operations:
            result = self.mongo_collection.bulk_write(operations)
            logger.info(f"MongoDB: {result.upserted_count} inseridas, {result.modified_count} atualizadas")

    def load_to_qdrant(self, questions: List[Dict[str, Any]]) -> Dict[str, str]:
        """Carrega embeddings no Qdrant, retorna mapeamento question_id -> embedding_id"""
        points = []
        id_mapping = {}

        for q in questions:
            if '_embedding' not in q:
                continue

            # Gera ID único para o embedding
            embedding_id = str(uuid.uuid4())
            id_mapping[q['question_id']] = embedding_id

            # Prepara payload (metadata)
            subject_area = q.get('subject_area', [])
            payload = {
                'question_id': q['question_id'],
                'exam': q.get('exam', ''),
                'subject_area': subject_area,
                'subject_discipline': subject_area[1] if len(subject_area) > 1 else '',  # Disciplina específica
                'specific_topic': q.get('specific_topic', ''),
                'difficulty': q.get('difficulty', ''),
                'year': q.get('year', None),
                'day': q.get('day', None),
                'retake': q.get('retake', False),
                'keywords': q.get('keywords', []),
                'has_images': bool(q.get('images', []))
            }

            points.append(
                PointStruct(
                    id=embedding_id,
                    vector=q['_embedding'],
                    payload=payload
                )
            )

        if points:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Qdrant: {len(points)} embeddings inseridos")

        return id_mapping

    def update_sqlite_references(self, questions: List[Dict[str, Any]], embedding_map: Dict[str, str]) -> None:
        """Atualiza referências no SQLite"""
        from app.models import QuestionReference

        for q in questions:
            # Pega o year e garante que é None se estiver vazio
            year = q.get('year')
            if year == '' or year == 0:
                year = None

            defaults = {
                'source_file': q.get('_source_file', ''),
                'exam': q.get('exam', ''),
                'subject_area': q.get('subject_area', []),
                'difficulty': q.get('difficulty', 'Médio'),
                'year': year,
                'is_processed': True,
                'embedding_id': embedding_map.get(q['question_id'])
            }

            QuestionReference.objects.update_or_create(
                question_id=q['question_id'],
                defaults=defaults
            )

        logger.info(f"SQLite: {len(questions)} referências atualizadas")