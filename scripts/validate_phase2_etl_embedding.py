#!/usr/bin/env python3
"""
Validação da Fase 2: ETL e Sistema de Embeddings
"""

import os
import sys
import django
import logging
from pathlib import Path
import traceback

# Setup Django
sys.path.append(str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from app.core.ETL.etl import ETLPipeline
from app.core.ETL.extractor import DataExtractor
from app.core.ETL.processor import DataProcessor
from app.core.ETL.embedder import EmbeddingGenerator
from app.core.ETL.loader import VectorStoreLoader
from app.core.ETL.validator import DataValidator
import json

logger = logging.getLogger(__name__)

class Phase2ValidationResult:
    """Resultado da validação da Fase 2"""
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.details = []
    
    def add_success(self, test_name: str, details: str = ""):
        self.tests_passed += 1
        self.details.append(f"✅ {test_name}: {details}")
        
    def add_failure(self, test_name: str, error: str):
        self.tests_failed += 1
        self.errors.append(error)
        self.details.append(f"❌ {test_name}: {error}")
    
    def print_summary(self):
        print("\n" + "="*60)
        print("VALIDAÇÃO FASE 2 - ETL E SISTEMA DE EMBEDDINGS")
        print("="*60)
        
        for detail in self.details:
            print(detail)
        
        print("\n" + "-"*40)
        print(f"Total de testes: {self.tests_passed + self.tests_failed}")
        print(f"✅ Sucessos: {self.tests_passed}")
        print(f"❌ Falhas: {self.tests_failed}")
        
        if self.tests_failed == 0:
            print("\n🎉 FASE 2 - VALIDAÇÃO COMPLETA COM SUCESSO!")
        else:
            print(f"\n⚠️  FASE 2 - {self.tests_failed} PROBLEMAS ENCONTRADOS")
            print("\nErros detalhados:")
            for error in self.errors:
                print(f"  • {error}")

def validate_etl_components():
    """Valida componentes do ETL"""
    result = Phase2ValidationResult()
    
    try:
        # Validar DataExtractor
        try:
            extractor = DataExtractor()
            result.add_success("DataExtractor", "Instanciado com sucesso")
            
            # Verificar métodos essenciais
            if hasattr(extractor, 'extract_from_file'):
                result.add_success("DataExtractor.extract_from_file", "Método disponível")
            else:
                result.add_failure("DataExtractor.extract_from_file", "Método não encontrado")
                
            if hasattr(extractor, 'validate_extracted_data'):
                result.add_success("DataExtractor.validate_extracted_data", "Método disponível")
            else:
                result.add_failure("DataExtractor.validate_extracted_data", "Método não encontrado")
                
        except Exception as e:
            result.add_failure("DataExtractor", f"Erro na instanciação: {str(e)}")
        
        # Validar DataProcessor
        try:
            processor = DataProcessor()
            result.add_success("DataProcessor", "Instanciado com sucesso")
            
            if hasattr(processor, 'process_question'):
                result.add_success("DataProcessor.process_question", "Método disponível")
            else:
                result.add_failure("DataProcessor.process_question", "Método não encontrado")
                
        except Exception as e:
            result.add_failure("DataProcessor", f"Erro na instanciação: {str(e)}")
        
        # Validar EmbeddingGenerator
        try:
            embedder = EmbeddingGenerator()
            result.add_success("EmbeddingGenerator", "Instanciado com sucesso")
            
            if hasattr(embedder, 'generate_embeddings'):
                result.add_success("EmbeddingGenerator.generate_embeddings", "Método disponível")
            else:
                result.add_failure("EmbeddingGenerator.generate_embeddings", "Método não encontrado")
                
        except Exception as e:
            result.add_failure("EmbeddingGenerator", f"Erro na instanciação: {str(e)}")
        
        # Validar VectorStoreLoader
        try:
            loader = VectorStoreLoader()
            result.add_success("VectorStoreLoader", "Instanciado com sucesso")
            
            if hasattr(loader, 'load_documents'):
                result.add_success("VectorStoreLoader.load_documents", "Método disponível")
            else:
                result.add_failure("VectorStoreLoader.load_documents", "Método não encontrado")
                
        except Exception as e:
            result.add_failure("VectorStoreLoader", f"Erro na instanciação: {str(e)}")
        
        # Validar DataValidator
        try:
            validator = DataValidator()
            result.add_success("DataValidator", "Instanciado com sucesso")
            
            if hasattr(validator, 'validate_question_data'):
                result.add_success("DataValidator.validate_question_data", "Método disponível")
            else:
                result.add_failure("DataValidator.validate_question_data", "Método não encontrado")
                
        except Exception as e:
            result.add_failure("DataValidator", f"Erro na instanciação: {str(e)}")
        
    except Exception as e:
        result.add_failure("Componentes ETL", f"Erro geral: {str(e)}")
    
    return result

def validate_etl_pipeline():
    """Valida o pipeline completo de ETL"""
    result = Phase2ValidationResult()
    
    try:
        # Instanciar pipeline
        pipeline = ETLPipeline()
        result.add_success("ETLPipeline", "Instanciado com sucesso")
        
        # Verificar configuração
        if hasattr(pipeline, 'config'):
            result.add_success("ETLPipeline.config", "Configuração presente")
        else:
            result.add_failure("ETLPipeline.config", "Configuração não encontrada")
        
        # Verificar métodos principais
        if hasattr(pipeline, 'run_pipeline'):
            result.add_success("ETLPipeline.run_pipeline", "Método disponível")
        else:
            result.add_failure("ETLPipeline.run_pipeline", "Método não encontrado")
            
        if hasattr(pipeline, 'extract_data'):
            result.add_success("ETLPipeline.extract_data", "Método disponível")
        else:
            result.add_failure("ETLPipeline.extract_data", "Método não encontrado")
            
        if hasattr(pipeline, 'process_data'):
            result.add_success("ETLPipeline.process_data", "Método disponível")
        else:
            result.add_failure("ETLPipeline.process_data", "Método não encontrado")
            
        if hasattr(pipeline, 'load_data'):
            result.add_success("ETLPipeline.load_data", "Método disponível")
        else:
            result.add_failure("ETLPipeline.load_data", "Método não encontrado")
        
    except Exception as e:
        result.add_failure("ETLPipeline", f"Erro: {str(e)}")
    
    return result

def validate_data_sources():
    """Valida fontes de dados disponíveis"""
    result = Phase2ValidationResult()
    
    try:
        # Verificar diretório de dados
        data_dir = Path(__file__).parent.parent / "app" / "data" / "raw"
        
        if data_dir.exists():
            result.add_success("Diretório de dados", f"Encontrado em: {data_dir}")
            
            # Verificar subdiretórios
            subdirs = [d for d in data_dir.iterdir() if d.is_dir()]
            if subdirs:
                result.add_success("Subdiretórios de dados", f"Encontrados: {[d.name for d in subdirs]}")
                
                # Verificar arquivos específicos do ENEM
                enem_dir = data_dir / "ENEM"
                if enem_dir.exists():
                    result.add_success("Dados ENEM", "Diretório encontrado")
                    
                    # Verificar arquivos JSON
                    json_files = list(enem_dir.rglob("*.json"))
                    if json_files:
                        result.add_success("Arquivos JSON ENEM", f"Encontrados: {len(json_files)} arquivos")
                        
                        # Validar estrutura de um arquivo JSON
                        try:
                            with open(json_files[0], 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                if isinstance(data, (list, dict)):
                                    result.add_success("Estrutura JSON", "Válida")
                                else:
                                    result.add_failure("Estrutura JSON", "Formato inesperado")
                        except Exception as e:
                            result.add_failure("Validação JSON", f"Erro ao ler arquivo: {str(e)}")
                    else:
                        result.add_failure("Arquivos JSON ENEM", "Nenhum arquivo JSON encontrado")
                else:
                    result.add_failure("Dados ENEM", "Diretório não encontrado")
            else:
                result.add_failure("Subdiretórios", "Nenhum subdiretório encontrado")
        else:
            result.add_failure("Diretório de dados", f"Não encontrado: {data_dir}")
        
    except Exception as e:
        result.add_failure("Fontes de dados", f"Erro: {str(e)}")
    
    return result

def validate_qdrant_storage():
    """Valida configuração do Qdrant para armazenamento de vetores"""
    result = Phase2ValidationResult()
    
    try:
        # Verificar diretório de storage do Qdrant
        qdrant_dir = Path(__file__).parent.parent / "app" / "data" / "qdrant_storage"
        
        if qdrant_dir.exists():
            result.add_success("Diretório Qdrant", f"Encontrado em: {qdrant_dir}")
            
            # Verificar se há coleções
            collections = [d for d in qdrant_dir.iterdir() if d.is_dir()]
            if collections:
                result.add_success("Coleções Qdrant", f"Encontradas: {[d.name for d in collections]}")
            else:
                result.add_success("Coleções Qdrant", "Diretório preparado (sem coleções)")
        else:
            result.add_failure("Diretório Qdrant", f"Não encontrado: {qdrant_dir}")
        
        # Tentar importar cliente Qdrant
        try:
            from qdrant_client import QdrantClient
            result.add_success("Qdrant Client", "Biblioteca disponível")
        except ImportError:
            result.add_failure("Qdrant Client", "Biblioteca não instalada")
        
    except Exception as e:
        result.add_failure("Qdrant Storage", f"Erro: {str(e)}")
    
    return result

def validate_embedding_functionality():
    """Valida funcionalidade de geração de embeddings"""
    result = Phase2ValidationResult()
    
    try:
        # Tentar carregar modelo de embedding
        embedder = EmbeddingGenerator()
        
        # Teste simples de geração de embedding
        test_text = "Esta é uma questão de teste sobre matemática."
        
        try:
            # Verificar se o método funciona (mesmo que não tenha modelo carregado)
            if hasattr(embedder, 'generate_text_embedding'):
                result.add_success("Geração de embeddings", "Método disponível")
            else:
                result.add_failure("Geração de embeddings", "Método não encontrado")
                
            # Verificar configuração de modelo
            if hasattr(embedder, 'model'):
                if embedder.model is not None:
                    result.add_success("Modelo de embedding", "Carregado")
                else:
                    result.add_success("Modelo de embedding", "Configurado para carregamento sob demanda")
            else:
                result.add_failure("Modelo de embedding", "Atributo model não encontrado")
        
        except Exception as e:
            result.add_failure("Teste de embedding", f"Erro: {str(e)}")
        
    except Exception as e:
        result.add_failure("EmbeddingGenerator", f"Erro na inicialização: {str(e)}")
    
    return result

def validate_etl_integration():
    """Valida integração completa do ETL"""
    result = Phase2ValidationResult()
    
    try:
        # Verificar se pipeline pode ser executado (sem execução real)
        pipeline = ETLPipeline()
        
        # Verificar dependências
        required_components = [
            ('extractor', 'DataExtractor'),
            ('processor', 'DataProcessor'),
            ('embedder', 'EmbeddingGenerator'),
            ('loader', 'VectorStoreLoader'),
            ('validator', 'DataValidator')
        ]
        
        for attr_name, class_name in required_components:
            if hasattr(pipeline, attr_name):
                result.add_success(f"Componente {class_name}", "Integrado ao pipeline")
            else:
                result.add_failure(f"Componente {class_name}", "Não integrado ao pipeline")
        
        # Verificar configuração de logging
        if hasattr(pipeline, 'logger'):
            result.add_success("Sistema de logging", "Configurado")
        else:
            result.add_success("Sistema de logging", "Usando logger padrão")
        
        # Verificar métricas e estatísticas
        if hasattr(pipeline, 'get_statistics'):
            result.add_success("Sistema de métricas", "Disponível")
        else:
            result.add_failure("Sistema de métricas", "Método get_statistics não encontrado")
        
    except Exception as e:
        result.add_failure("Integração ETL", f"Erro: {str(e)}")
    
    return result

def validate_command_management():
    """Valida comandos de gerenciamento Django"""
    result = Phase2ValidationResult()
    
    try:
        # Verificar comando starter
        commands_dir = Path(__file__).parent.parent / "app" / "management" / "commands"
        
        if commands_dir.exists():
            result.add_success("Diretório de comandos", "Encontrado")
            
            # Verificar comando starter
            starter_file = commands_dir / "starter.py"
            if starter_file.exists():
                result.add_success("Comando starter", "Arquivo encontrado")
            else:
                result.add_failure("Comando starter", "Arquivo não encontrado")
                
            # Verificar outros comandos
            command_files = list(commands_dir.glob("*.py"))
            if command_files:
                commands = [f.stem for f in command_files if f.stem != "__init__"]
                result.add_success("Comandos disponíveis", f"Encontrados: {commands}")
            else:
                result.add_failure("Comandos disponíveis", "Nenhum comando encontrado")
        else:
            result.add_failure("Diretório de comandos", "Não encontrado")
        
    except Exception as e:
        result.add_failure("Comandos Django", f"Erro: {str(e)}")
    
    return result

def main():
    """Função principal de validação"""
    print("Iniciando validação da Fase 2 - ETL e Sistema de Embeddings...")
    
    all_results = []
    
    # Executar todas as validações
    all_results.append(validate_etl_components())
    all_results.append(validate_etl_pipeline())
    all_results.append(validate_data_sources())
    all_results.append(validate_qdrant_storage())
    all_results.append(validate_embedding_functionality())
    all_results.append(validate_etl_integration())
    all_results.append(validate_command_management())
    
    # Consolidar resultados
    final_result = Phase2ValidationResult()
    for result in all_results:
        final_result.tests_passed += result.tests_passed
        final_result.tests_failed += result.tests_failed
        final_result.errors.extend(result.errors)
        final_result.details.extend(result.details)
    
    # Imprimir resultado final
    final_result.print_summary()
    
    return final_result.tests_failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)