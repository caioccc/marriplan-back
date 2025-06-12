import logging
import os
import sys
import threading

from django.apps import AppConfig

from app.core.constants import LOGGING_LEVEL
from app.core.models.llm.ollama import check_ollama
from app.core.models.utils import init_models


class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"

    def ready(self):
        """Executado quando a aplicação Django está pronta"""

        # Detecta se estamos no processo principal do Django
        if os.environ.get('RUN_MAIN') != 'true':
            return  # Ignora o processo de setup do reloader

        # Importa aqui para evitar importação circular
        from django.conf import settings

        # Só executa ETL se não estiver em modo de migração
        if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
            # Executa ETL em thread separada para não bloquear startup
            if getattr(settings, 'RUN_ETL_ON_STARTUP', True):
                thread = threading.Thread(target=self.run_etl_pipeline)
                thread.daemon = True
                thread.start()

        # Configuração global de logs
        logging.basicConfig(
            level=logging.getLevelName(LOGGING_LEVEL),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Check if the ollama tool and LLM core are ready to use
        check_ollama()

        # Load models
        init_models()

        # Importa utils para garantir que o patch do httpx seja aplicado
        import app.core.models.utils  # noqa: F401

    def run_etl_pipeline(self):
        """Executa pipeline ETL em background"""
        try:
            # Aguarda um pouco para garantir que Django está completamente inicializado
            import time
            time.sleep(2)

            from app.core.ETL.etl import ETLPipeline
            logging.info("Iniciando verificação ETL...")

            pipeline = ETLPipeline()
            pipeline.run(force=False)  # Processa apenas questões novas

        except Exception as e:
            logging.error(f"Erro ao executar pipeline ETL: {e}", exc_info=True)
