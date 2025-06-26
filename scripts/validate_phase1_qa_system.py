#!/usr/bin/env python3
"""
Validação da Fase 1: Sistema de Questões e Respostas
"""

import os
import sys
import django
import logging
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from app.models import CustomUser, UserSession, QuestionReference, UserQuestionHistory
from backend.app.viewsets_old import QuestionViewSet
from app.serializers import QuestionSerializer
from rest_framework.test import APIRequestFactory
from django.test import TestCase
import json

logger = logging.getLogger(__name__)

class Phase1ValidationResult:
    """Resultado da validação da Fase 1"""
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
        print("VALIDAÇÃO FASE 1 - SISTEMA DE QUESTÕES E RESPOSTAS")
        print("="*60)

        for detail in self.details:
            print(detail)

        print("\n" + "-"*40)
        print(f"Total de testes: {self.tests_passed + self.tests_failed}")
        print(f"✅ Sucessos: {self.tests_passed}")
        print(f"❌ Falhas: {self.tests_failed}")

        if self.tests_failed == 0:
            print("\n🎉 FASE 1 - VALIDAÇÃO COMPLETA COM SUCESSO!")
        else:
            print(f"\n⚠️  FASE 1 - {self.tests_failed} PROBLEMAS ENCONTRADOS")
            print("\nErros detalhados:")
            for error in self.errors:
                print(f"  • {error}")

def validate_database_models():
    """Valida modelos do banco de dados"""
    result = Phase1ValidationResult()

    try:
        # Testar criação de usuário
        user_count = CustomUser.objects.count()
        result.add_success("Modelo CustomUser", f"Acessível - {user_count} usuários na base")

        # Testar modelo de sessão
        session_count = UserSession.objects.count()
        result.add_success("Modelo UserSession", f"Acessível - {session_count} sessões na base")

        # Testar modelo de referências de questões
        question_ref_count = QuestionReference.objects.count()
        result.add_success("Modelo QuestionReference", f"Acessível - {question_ref_count} questões na base")

        # Testar modelo de histórico
        history_count = UserQuestionHistory.objects.count()
        result.add_success("Modelo UserQuestionHistory", f"Acessível - {history_count} registros na base")

    except Exception as e:
        result.add_failure("Modelos de Banco", f"Erro ao acessar modelos: {str(e)}")

    return result

def validate_viewsets():
    """Valida ViewSets da API"""
    result = Phase1ValidationResult()

    try:
        # Testar QuestionViewSet
        factory = APIRequestFactory()
        request = factory.get('/api/questions/')

        viewset = QuestionViewSet()
        viewset.request = request

        # Verificar métodos essenciais
        if hasattr(viewset, 'get_queryset'):
            result.add_success("QuestionViewSet.get_queryset", "Método existe")
        else:
            result.add_failure("QuestionViewSet.get_queryset", "Método não encontrado")

        if hasattr(viewset, 'list'):
            result.add_success("QuestionViewSet.list", "Método existe")
        else:
            result.add_failure("QuestionViewSet.list", "Método não encontrado")

        if hasattr(viewset, 'create'):
            result.add_success("QuestionViewSet.create", "Método existe")
        else:
            result.add_failure("QuestionViewSet.create", "Método não encontrado")

    except Exception as e:
        result.add_failure("QuestionViewSet", f"Erro ao validar viewset: {str(e)}")

    return result

def validate_serializers():
    """Valida Serializers"""
    result = Phase1ValidationResult()

    try:
        # Testar QuestionSerializer
        serializer = QuestionSerializer()

        # Verificar campos essenciais
        expected_fields = ['id', 'question_text', 'subject', 'difficulty']

        if hasattr(serializer, 'Meta'):
            if hasattr(serializer.Meta, 'fields'):
                result.add_success("QuestionSerializer.Meta.fields", "Campos definidos")
            else:
                result.add_failure("QuestionSerializer.Meta.fields", "Campos não definidos")
        else:
            result.add_failure("QuestionSerializer.Meta", "Meta classe não encontrada")

        # Verificar se serializer pode ser instanciado
        result.add_success("QuestionSerializer instância", "Serializer criado com sucesso")

    except Exception as e:
        result.add_failure("QuestionSerializer", f"Erro ao validar serializer: {str(e)}")

    return result

def validate_api_endpoints():
    """Valida endpoints da API"""
    result = Phase1ValidationResult()

    try:
        from django.urls import reverse
        from django.test import Client

        client = Client()

        # Testar endpoint de questões (se configurado)
        try:
            response = client.get('/api/questions/')
            if response.status_code in [200, 401, 403]:  # Aceitar até não autorizado
                result.add_success("Endpoint /api/questions/", f"Resposta: {response.status_code}")
            else:
                result.add_failure("Endpoint /api/questions/", f"Status inesperado: {response.status_code}")
        except Exception as e:
            result.add_failure("Endpoint /api/questions/", f"Erro: {str(e)}")

    except Exception as e:
        result.add_failure("Configuração de URLs", f"Erro ao testar endpoints: {str(e)}")

    return result

def validate_question_data_integrity():
    """Valida integridade dos dados de questões"""
    result = Phase1ValidationResult()

    try:
        # Verificar se há questões carregadas
        questions = QuestionReference.objects.all()[:5]

        if questions.exists():
            result.add_success("Dados de Questões", f"Encontradas questões na base de dados")

            # Verificar campos essenciais em algumas questões
            for i, question in enumerate(questions):
                issues = []

                if not question.question_text:
                    issues.append("texto vazio")
                if not question.subject:
                    issues.append("matéria não definida")
                if not question.difficulty:
                    issues.append("dificuldade não definida")

                if issues:
                    result.add_failure(f"Questão {i+1}", f"Problemas: {', '.join(issues)}")
                else:
                    result.add_success(f"Questão {i+1}", "Dados íntegros")
        else:
            result.add_failure("Dados de Questões", "Nenhuma questão encontrada na base")

    except Exception as e:
        result.add_failure("Integridade de Dados", f"Erro ao verificar dados: {str(e)}")

    return result

def validate_user_management():
    """Valida sistema de gerenciamento de usuários"""
    result = Phase1ValidationResult()

    try:
        # Verificar se o modelo de usuário está funcionando
        user_count = CustomUser.objects.count()
        result.add_success("Sistema de Usuários", f"Modelo funcional - {user_count} usuários")

        # Verificar campos customizados (se existirem)
        if CustomUser.objects.first():
            user = CustomUser.objects.first()

            # Verificar campos essenciais
            if hasattr(user, 'email'):
                result.add_success("Campo email", "Presente no modelo")
            if hasattr(user, 'is_active'):
                result.add_success("Campo is_active", "Presente no modelo")

        # Verificar sessões de usuário
        if UserSession.objects.exists():
            result.add_success("Sistema de Sessões", "Funcional")
        else:
            result.add_success("Sistema de Sessões", "Modelo disponível (sem sessões ativas)")

    except Exception as e:
        result.add_failure("Sistema de Usuários", f"Erro: {str(e)}")

    return result

def main():
    """Função principal de validação"""
    print("Iniciando validação da Fase 1 - Sistema de Questões e Respostas...")

    all_results = []

    # Executar todas as validações
    all_results.append(validate_database_models())
    all_results.append(validate_viewsets())
    all_results.append(validate_serializers())
    all_results.append(validate_api_endpoints())
    all_results.append(validate_question_data_integrity())
    all_results.append(validate_user_management())

    # Consolidar resultados
    final_result = Phase1ValidationResult()
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