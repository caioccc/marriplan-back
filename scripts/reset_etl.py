#!/usr/bin/env python
"""
Script para limpar dados antigos e reprocessar ETL

Uso:
    python scripts/reset_etl.py
"""

import os
import sys
import django

# Adicionar o diretório pai ao path para importações
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.conf import settings
from pymongo import MongoClient
from qdrant_client import QdrantClient
from app.models import QuestionReference
from app.core.ETL.etl import ETLPipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_all_data():
    """Limpa todos os dados de questões dos bancos"""

    # 1. Limpar SQLite
    logger.info("Limpando referências do SQLite...")
    QuestionReference.objects.all().delete()
    logger.info("SQLite limpo!")

    # 2. Limpar MongoDB
    logger.info("Limpando MongoDB...")
    mongo_client = MongoClient(getattr(settings, 'MONGODB_URL', 'mongodb://localhost:27017/'))
    mongo_db = mongo_client[getattr(settings, 'MONGODB_DB', 'marriplan')]
    mongo_db['questions'].delete_many({})
    logger.info("MongoDB limpo!")

    # 3. Limpar Qdrant
    logger.info("Limpando Qdrant...")
    qdrant_client = QdrantClient(
        host=getattr(settings, 'QDRANT_HOST', 'localhost'),
        port=getattr(settings, 'QDRANT_PORT', 6333)
    )

    try:
        # Deletar collection se existir
        collections = qdrant_client.get_collections().collections
        if any(c.name == 'questions' for c in collections):
            qdrant_client.delete_collection(collection_name='questions')
            logger.info("Collection 'questions' deletada do Qdrant!")
    except Exception as e:
        logger.warning(f"Erro ao limpar Qdrant: {e}")


def run_new_etl():
    """Executa o ETL do zero"""
    logger.info("\n=== Iniciando novo ETL ===")

    pipeline = ETLPipeline()
    pipeline.run(force=True)  # Force=True para processar tudo

    logger.info("\n=== ETL concluído! ===")


if __name__ == "__main__":
    print("\n" + "="*50)
    print("RESET ETL - Limpeza e Reprocessamento")
    print("="*50 + "\n")

    # Confirmar ação
    response = input("Isso irá DELETAR todos os dados de questões. Continuar? (s/N): ")

    if response.lower() == 's':
        clean_all_data()
        run_new_etl()
        print("\n✅ Reset concluído com sucesso!")
    else:
        print("\n❌ Operação cancelada.")