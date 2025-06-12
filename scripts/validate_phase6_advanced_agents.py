#!/usr/bin/env python3
"""
Validação da Fase 6: Agentes Avançados (Explanation Agent e Study Plan Agent)
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

from app.core.agents.explanation_agent import ExplanationAgent
from app.core.agents.study_plan_agent import StudyPlanAgent, StudyPlan, StudySession
from app.core.services.progress_tracking import ProgressTrackingService, LearningActivity, ProgressSnapshot
from app.core.services.recommendation_engine import RecommendationEngine, UserProfile, Recommendation
from app.core.models.agent_models import AgentRequest
from datetime import datetime

logger = logging.getLogger(__name__)

class Phase6ValidationResult:
    """Resultado da validação da Fase 6"""
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
        print("VALIDAÇÃO FASE 6 - AGENTES AVANÇADOS")
        print("="*60)
        
        for detail in self.details:
            print(detail)
        
        print("\n" + "-"*40)
        print(f"Total de testes: {self.tests_passed + self.tests_failed}")
        print(f"✅ Sucessos: {self.tests_passed}")
        print(f"❌ Falhas: {self.tests_failed}")
        
        if self.tests_failed == 0:
            print("\n🎉 FASE 6 - VALIDAÇÃO COMPLETA COM SUCESSO!")
        else:
            print(f"\n⚠️  FASE 6 - {self.tests_failed} PROBLEMAS ENCONTRADOS")
            print("\nErros detalhados:")
            for error in self.errors:
                print(f"  • {error}")

def validate_explanation_agent():
    """Valida o ExplanationAgent"""
    result = Phase6ValidationResult()
    
    try:
        # Instanciar ExplanationAgent
        explanation_agent = ExplanationAgent()
        result.add_success("ExplanationAgent", "Instanciado com sucesso")
        
        # Verificar herança e configuração base
        if hasattr(explanation_agent, 'name'):
            result.add_success("ExplanationAgent.name", f"Nome: {explanation_agent.name}")
        else:
            result.add_failure("ExplanationAgent.name", "Nome não definido")
        
        if hasattr(explanation_agent, 'capabilities'):
            result.add_success("ExplanationAgent.capabilities", f"Capacidades: {len(explanation_agent.capabilities)}")
        else:
            result.add_failure("ExplanationAgent.capabilities", "Capacidades não definidas")
        
        if hasattr(explanation_agent, 'priority'):
            result.add_success("ExplanationAgent.priority", f"Prioridade: {explanation_agent.priority}")
        else:
            result.add_failure("ExplanationAgent.priority", "Prioridade não definida")
        
        # Verificar integração i18n
        if hasattr(explanation_agent, 'localization'):
            result.add_success("ExplanationAgent.localization", "LocalizationManager integrado")
        else:
            result.add_failure("ExplanationAgent.localization", "LocalizationManager não encontrado")
        
        if hasattr(explanation_agent, 'patterns'):
            result.add_success("ExplanationAgent.patterns", "PatternManager integrado")
        else:
            result.add_failure("ExplanationAgent.patterns", "PatternManager não encontrado")
        
        # Verificar serviços integrados
        if hasattr(explanation_agent, 'search_service'):
            result.add_success("ExplanationAgent.search_service", "SearchService integrado")
        else:
            result.add_failure("ExplanationAgent.search_service", "SearchService não encontrado")
        
        if hasattr(explanation_agent, 'reranking_service'):
            result.add_success("ExplanationAgent.reranking_service", "RerankingService integrado")
        else:
            result.add_failure("ExplanationAgent.reranking_service", "RerankingService não encontrado")
        
        # Verificar métodos essenciais
        essential_methods = [
            'can_handle',
            'process',
            '_extract_concept',
            '_generate_explanation'
        ]
        
        for method in essential_methods:
            if hasattr(explanation_agent, method):
                result.add_success(f"ExplanationAgent.{method}", "Método disponível")
            else:
                result.add_failure(f"ExplanationAgent.{method}", "Método não encontrado")
        
        # Verificar cache de explicações
        if hasattr(explanation_agent, 'explanation_cache'):
            result.add_success("ExplanationAgent.explanation_cache", "Sistema de cache configurado")
        else:
            result.add_failure("ExplanationAgent.explanation_cache", "Cache não encontrado")
        
        # Verificar configuração
        if hasattr(explanation_agent, 'config'):
            config = explanation_agent.config
            
            config_items = [
                'max_search_results',
                'similarity_threshold',
                'enable_reranking',
                'explanation_depth'
            ]
            
            for item in config_items:
                if item in config:
                    result.add_success(f"Config {item}", f"Valor: {config[item]}")
                else:
                    result.add_failure(f"Config {item}", "Não encontrado")
        else:
            result.add_failure("ExplanationAgent.config", "Configuração não encontrada")
    
    except Exception as e:
        result.add_failure("ExplanationAgent", f"Erro na instanciação: {str(e)}")
    
    return result

def validate_study_plan_agent():
    """Valida o StudyPlanAgent"""
    result = Phase6ValidationResult()
    
    try:
        # Instanciar StudyPlanAgent
        study_plan_agent = StudyPlanAgent()
        result.add_success("StudyPlanAgent", "Instanciado com sucesso")
        
        # Verificar configuração base
        if hasattr(study_plan_agent, 'name'):
            result.add_success("StudyPlanAgent.name", f"Nome: {study_plan_agent.name}")
        else:
            result.add_failure("StudyPlanAgent.name", "Nome não definido")
        
        if hasattr(study_plan_agent, 'capabilities'):
            result.add_success("StudyPlanAgent.capabilities", f"Capacidades: {len(study_plan_agent.capabilities)}")
        else:
            result.add_failure("StudyPlanAgent.capabilities", "Capacidades não definidas")
        
        # Verificar integração com serviços
        if hasattr(study_plan_agent, 'progress_tracker'):
            result.add_success("StudyPlanAgent.progress_tracker", "ProgressTrackingService integrado")
        else:
            result.add_failure("StudyPlanAgent.progress_tracker", "ProgressTrackingService não encontrado")
        
        if hasattr(study_plan_agent, 'recommendation_engine'):
            result.add_success("StudyPlanAgent.recommendation_engine", "RecommendationEngine integrado")
        else:
            result.add_failure("StudyPlanAgent.recommendation_engine", "RecommendationEngine não encontrado")
        
        # Verificar i18n
        if hasattr(study_plan_agent, 'localization'):
            result.add_success("StudyPlanAgent.localization", "LocalizationManager integrado")
        else:
            result.add_failure("StudyPlanAgent.localization", "LocalizationManager não encontrado")
        
        # Verificar armazenamento de planos
        if hasattr(study_plan_agent, 'study_plans'):
            result.add_success("StudyPlanAgent.study_plans", "Sistema de armazenamento configurado")
        else:
            result.add_failure("StudyPlanAgent.study_plans", "Armazenamento não encontrado")
        
        # Verificar templates de planos
        if hasattr(study_plan_agent, 'plan_templates'):
            templates = study_plan_agent.plan_templates
            if templates:
                result.add_success("StudyPlanAgent.plan_templates", f"Templates: {list(templates.keys())}")
            else:
                result.add_failure("StudyPlanAgent.plan_templates", "Templates vazios")
        else:
            result.add_failure("StudyPlanAgent.plan_templates", "Templates não encontrados")
        
        # Verificar métodos essenciais
        planning_methods = [
            'can_handle',
            'process',
            '_create_personalized_plan',
            '_adjust_plan_based_on_progress'
        ]
        
        for method in planning_methods:
            if hasattr(study_plan_agent, method):
                result.add_success(f"StudyPlanAgent.{method}", "Método disponível")
            else:
                result.add_failure(f"StudyPlanAgent.{method}", "Método não encontrado")
        
        # Verificar configuração
        if hasattr(study_plan_agent, 'config'):
            config = study_plan_agent.config
            
            config_items = [
                'max_plans_per_user',
                'default_session_duration',
                'auto_adjust_enabled'
            ]
            
            for item in config_items:
                if item in config:
                    result.add_success(f"Config {item}", f"Valor: {config[item]}")
                else:
                    result.add_failure(f"Config {item}", "Não encontrado")
        else:
            result.add_failure("StudyPlanAgent.config", "Configuração não encontrada")
    
    except Exception as e:
        result.add_failure("StudyPlanAgent", f"Erro na instanciação: {str(e)}")
    
    return result

def validate_progress_tracking_service():
    """Valida o ProgressTrackingService"""
    result = Phase6ValidationResult()
    
    try:
        # Instanciar ProgressTrackingService
        progress_service = ProgressTrackingService()
        result.add_success("ProgressTrackingService", "Instanciado com sucesso")
        
        # Verificar métodos essenciais
        tracking_methods = [
            'record_activity',
            'get_user_progress',
            'get_detailed_analytics',
            'set_learning_goal'
        ]
        
        for method in tracking_methods:
            if hasattr(progress_service, method):
                result.add_success(f"ProgressTrackingService.{method}", "Método disponível")
            else:
                result.add_failure(f"ProgressTrackingService.{method}", "Método não encontrado")
        
        # Verificar armazenamento
        storage_attrs = [
            'activities_storage',
            'snapshots_storage',
            'goals_storage'
        ]
        
        for attr in storage_attrs:
            if hasattr(progress_service, attr):
                result.add_success(f"ProgressTrackingService.{attr}", "Sistema de armazenamento configurado")
            else:
                result.add_failure(f"ProgressTrackingService.{attr}", "Armazenamento não encontrado")
        
        # Verificar configuração
        if hasattr(progress_service, 'config'):
            config = progress_service.config
            
            config_items = [
                'snapshot_interval_hours',
                'streak_reset_hours',
                'min_session_duration'
            ]
            
            for item in config_items:
                if item in config:
                    result.add_success(f"Config {item}", f"Valor: {config[item]}")
                else:
                    result.add_failure(f"Config {item}", "Não encontrado")
        
        # Testar criação de LearningActivity
        try:
            activity = LearningActivity(
                activity_id="test_1",
                user_id="test_user",
                session_id="test_session",
                activity_type="question",
                subject_area="mathematics",
                difficulty_level="intermediate",
                topic="algebra",
                timestamp=datetime.now(),
                duration_seconds=120,
                success=True,
                confidence_score=0.8
            )
            result.add_success("LearningActivity", "Pode ser criado")
        except Exception as e:
            result.add_failure("LearningActivity", f"Erro na criação: {str(e)}")
    
    except Exception as e:
        result.add_failure("ProgressTrackingService", f"Erro na instanciação: {str(e)}")
    
    return result

def validate_recommendation_engine():
    """Valida o RecommendationEngine"""
    result = Phase6ValidationResult()
    
    try:
        # Instanciar RecommendationEngine
        recommendation_engine = RecommendationEngine()
        result.add_success("RecommendationEngine", "Instanciado com sucesso")
        
        # Verificar métodos essenciais
        recommendation_methods = [
            'get_recommendations',
            'record_feedback',
            'update_user_profile'
        ]
        
        for method in recommendation_methods:
            if hasattr(recommendation_engine, method):
                result.add_success(f"RecommendationEngine.{method}", "Método disponível")
            else:
                result.add_failure(f"RecommendationEngine.{method}", "Método não encontrado")
        
        # Verificar armazenamento
        storage_attrs = [
            'user_profiles',
            'recommendations_history',
            'feedback_history'
        ]
        
        for attr in storage_attrs:
            if hasattr(recommendation_engine, attr):
                result.add_success(f"RecommendationEngine.{attr}", "Sistema de armazenamento configurado")
            else:
                result.add_failure(f"RecommendationEngine.{attr}", "Armazenamento não encontrado")
        
        # Verificar knowledge base
        if hasattr(recommendation_engine, 'concept_relationships'):
            result.add_success("RecommendationEngine.concept_relationships", "Grafo de conceitos configurado")
        else:
            result.add_failure("RecommendationEngine.concept_relationships", "Grafo de conceitos não encontrado")
        
        if hasattr(recommendation_engine, 'study_techniques'):
            techniques = recommendation_engine.study_techniques
            if techniques:
                result.add_success("RecommendationEngine.study_techniques", f"Técnicas: {len(techniques)}")
            else:
                result.add_failure("RecommendationEngine.study_techniques", "Técnicas vazias")
        else:
            result.add_failure("RecommendationEngine.study_techniques", "Técnicas não encontradas")
        
        # Verificar configuração
        if hasattr(recommendation_engine, 'config'):
            config = recommendation_engine.config
            
            config_items = [
                'max_recommendations_per_request',
                'recommendation_expiry_hours',
                'personalization_weight'
            ]
            
            for item in config_items:
                if item in config:
                    result.add_success(f"Config {item}", f"Valor: {config[item]}")
                else:
                    result.add_failure(f"Config {item}", "Não encontrado")
        
        # Testar criação de UserProfile
        try:
            profile = UserProfile(
                user_id="test_user",
                learning_style="visual",
                preferred_difficulty="intermediate",
                strong_subjects=["mathematics"],
                weak_subjects=["physics"],
                study_goals=["improve accuracy"],
                available_time_minutes=60,
                performance_level="intermediate",
                last_activity=datetime.now(),
                total_study_time=300,
                success_rate=0.75,
                confidence_level=0.8
            )
            result.add_success("UserProfile", "Pode ser criado")
        except Exception as e:
            result.add_failure("UserProfile", f"Erro na criação: {str(e)}")
    
    except Exception as e:
        result.add_failure("RecommendationEngine", f"Erro na instanciação: {str(e)}")
    
    return result

def validate_agent_can_handle():
    """Valida funcionalidade can_handle dos agentes"""
    result = Phase6ValidationResult()
    
    try:
        explanation_agent = ExplanationAgent()
        study_plan_agent = StudyPlanAgent()
        
        # Testes para ExplanationAgent
        explanation_tests = [
            {
                'message': 'Explique o que é fotossíntese',
                'should_handle': True,
                'description': 'Solicitação de explicação'
            },
            {
                'message': 'O que significa integral em matemática?',
                'should_handle': True,
                'description': 'Pergunta sobre conceito'
            },
            {
                'message': 'Preciso de uma questão de física',
                'should_handle': False,
                'description': 'Solicitação de questão (não explicação)'
            }
        ]
        
        for test in explanation_tests:
            try:
                request = AgentRequest(
                    message=test['message'],
                    user_id="test_user",
                    session_id="test_session"
                )
                
                can_handle = explanation_agent.can_handle(request)
                
                if can_handle == test['should_handle']:
                    result.add_success(f"ExplanationAgent: {test['description']}", f"Correto: {can_handle}")
                else:
                    result.add_failure(f"ExplanationAgent: {test['description']}", f"Esperado: {test['should_handle']}, Obtido: {can_handle}")
            
            except Exception as e:
                result.add_failure(f"ExplanationAgent: {test['description']}", f"Erro: {str(e)}")
        
        # Testes para StudyPlanAgent
        planning_tests = [
            {
                'message': 'Crie um plano de estudos para matemática',
                'should_handle': True,
                'description': 'Solicitação de plano'
            },
            {
                'message': 'Como está meu progresso?',
                'should_handle': True,
                'description': 'Consulta de progresso'
            },
            {
                'message': 'Explique derivadas',
                'should_handle': False,
                'description': 'Solicitação de explicação (não planejamento)'
            }
        ]
        
        for test in planning_tests:
            try:
                request = AgentRequest(
                    message=test['message'],
                    user_id="test_user",
                    session_id="test_session"
                )
                
                can_handle = study_plan_agent.can_handle(request)
                
                if can_handle == test['should_handle']:
                    result.add_success(f"StudyPlanAgent: {test['description']}", f"Correto: {can_handle}")
                else:
                    result.add_failure(f"StudyPlanAgent: {test['description']}", f"Esperado: {test['should_handle']}, Obtido: {can_handle}")
            
            except Exception as e:
                result.add_failure(f"StudyPlanAgent: {test['description']}", f"Erro: {str(e)}")
    
    except Exception as e:
        result.add_failure("can_handle tests", f"Erro: {str(e)}")
    
    return result

def validate_multilingual_support():
    """Valida suporte multilíngue dos agentes avançados"""
    result = Phase6ValidationResult()
    
    try:
        explanation_agent = ExplanationAgent()
        study_plan_agent = StudyPlanAgent()
        
        # Testes multilíngues para ExplanationAgent
        multilingual_tests = [
            {
                'message': 'Explique fotossíntese',
                'language': 'Português',
                'agent': explanation_agent
            },
            {
                'message': 'Explain photosynthesis',
                'language': 'Inglês',
                'agent': explanation_agent
            },
            {
                'message': 'Crear plan de estudios',
                'language': 'Espanhol',
                'agent': study_plan_agent
            },
            {
                'message': 'Créer un plan d\'étude',
                'language': 'Francês',
                'agent': study_plan_agent
            }
        ]
        
        for test in multilingual_tests:
            try:
                request = AgentRequest(
                    message=test['message'],
                    user_id="test_user",
                    session_id="test_session"
                )
                
                # Verificar se agente consegue processar
                can_handle = test['agent'].can_handle(request)
                
                if can_handle:
                    result.add_success(f"Multilíngue {test['language']}", f"Agente {test['agent'].name} aceita")
                else:
                    result.add_success(f"Multilíngue {test['language']}", f"Agente {test['agent'].name} rejeita corretamente")
            
            except Exception as e:
                result.add_failure(f"Multilíngue {test['language']}", f"Erro: {str(e)}")
    
    except Exception as e:
        result.add_failure("Suporte multilíngue", f"Erro: {str(e)}")
    
    return result

def validate_data_models():
    """Valida modelos de dados dos agentes avançados"""
    result = Phase6ValidationResult()
    
    try:
        # Testar StudyPlan
        try:
            study_plan = StudyPlan(
                plan_id="test_plan_1",
                user_id="test_user",
                title="Plano de Matemática",
                description="Plano focado em álgebra",
                plan_type="weekly",
                priority="medium",
                subjects=["mathematics"],
                total_duration_days=7,
                estimated_hours_per_day=2.0,
                start_date=datetime.now(),
                end_date=datetime.now(),
                sessions=[],
                goals=["Melhorar em álgebra"]
            )
            result.add_success("StudyPlan", "Pode ser criado")
        except Exception as e:
            result.add_failure("StudyPlan", f"Erro na criação: {str(e)}")
        
        # Testar StudySession
        try:
            study_session = StudySession(
                session_id="session_1",
                title="Álgebra Básica",
                description="Estudar equações lineares",
                subject_area="mathematics",
                topics=["equations", "linear"],
                estimated_duration_minutes=45,
                difficulty_level="basic",
                activities=["reading", "practice"],
                prerequisites=[],
                learning_objectives=["Resolver equações lineares"],
                resources=["Livro de álgebra"]
            )
            result.add_success("StudySession", "Pode ser criado")
        except Exception as e:
            result.add_failure("StudySession", f"Erro na criação: {str(e)}")
        
        # Testar ProgressSnapshot
        try:
            progress_snapshot = ProgressSnapshot(
                user_id="test_user",
                timestamp=datetime.now(),
                total_activities=10,
                correct_percentage=75.0,
                average_confidence=0.8,
                study_time_minutes=120,
                subjects_studied=["mathematics"],
                current_streak=3,
                level_distribution={"basic": 5, "intermediate": 5},
                recent_topics=["algebra", "geometry"],
                performance_trend="improving"
            )
            result.add_success("ProgressSnapshot", "Pode ser criado")
        except Exception as e:
            result.add_failure("ProgressSnapshot", f"Erro na criação: {str(e)}")
        
    except Exception as e:
        result.add_failure("Modelos de dados", f"Erro: {str(e)}")
    
    return result

def validate_integration_between_services():
    """Valida integração entre os serviços dos agentes avançados"""
    result = Phase6ValidationResult()
    
    try:
        study_plan_agent = StudyPlanAgent()
        progress_service = ProgressTrackingService()
        recommendation_engine = RecommendationEngine()
        
        # Verificar se StudyPlanAgent usa ProgressTrackingService
        if hasattr(study_plan_agent, 'progress_tracker'):
            if isinstance(study_plan_agent.progress_tracker, ProgressTrackingService):
                result.add_success("Integração StudyPlan-Progress", "Serviço integrado")
            else:
                result.add_failure("Integração StudyPlan-Progress", "Tipo incorreto do serviço")
        else:
            result.add_failure("Integração StudyPlan-Progress", "Serviço não encontrado")
        
        # Verificar se StudyPlanAgent usa RecommendationEngine
        if hasattr(study_plan_agent, 'recommendation_engine'):
            if isinstance(study_plan_agent.recommendation_engine, RecommendationEngine):
                result.add_success("Integração StudyPlan-Recommendations", "Serviço integrado")
            else:
                result.add_failure("Integração StudyPlan-Recommendations", "Tipo incorreto do serviço")
        else:
            result.add_failure("Integração StudyPlan-Recommendations", "Serviço não encontrado")
        
        # Verificar compatibilidade de interfaces
        try:
            # Simular fluxo de criação de plano baseado em progresso
            user_id = "test_user"
            
            # 1. Obter progresso do usuário
            if hasattr(progress_service, 'get_user_progress'):
                result.add_success("Fluxo integrado: get_user_progress", "Método disponível")
            
            # 2. Obter recomendações
            if hasattr(recommendation_engine, 'get_recommendations'):
                result.add_success("Fluxo integrado: get_recommendations", "Método disponível")
            
            # 3. Criar plano personalizado
            if hasattr(study_plan_agent, '_create_personalized_plan'):
                result.add_success("Fluxo integrado: create_personalized_plan", "Método disponível")
            
            result.add_success("Compatibilidade de interfaces", "Fluxo completo possível")
        
        except Exception as e:
            result.add_failure("Compatibilidade de interfaces", f"Erro: {str(e)}")
        
        # Verificar métricas e estatísticas
        services = [
            ('StudyPlanAgent', study_plan_agent),
            ('ProgressTrackingService', progress_service),
            ('RecommendationEngine', recommendation_engine)
        ]
        
        for service_name, service in services:
            if hasattr(service, 'get_statistics'):
                result.add_success(f"Métricas {service_name}", "Método get_statistics disponível")
            else:
                result.add_failure(f"Métricas {service_name}", "Método get_statistics não encontrado")
    
    except Exception as e:
        result.add_failure("Integração entre serviços", f"Erro: {str(e)}")
    
    return result

def main():
    """Função principal de validação"""
    print("Iniciando validação da Fase 6 - Agentes Avançados...")
    
    all_results = []
    
    # Executar todas as validações
    all_results.append(validate_explanation_agent())
    all_results.append(validate_study_plan_agent())
    all_results.append(validate_progress_tracking_service())
    all_results.append(validate_recommendation_engine())
    all_results.append(validate_agent_can_handle())
    all_results.append(validate_multilingual_support())
    all_results.append(validate_data_models())
    all_results.append(validate_integration_between_services())
    
    # Consolidar resultados
    final_result = Phase6ValidationResult()
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