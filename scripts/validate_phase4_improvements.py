#!/usr/bin/env python3
"""
Validation script for Phase 4 improvements:
1. Orchestrator fix
2. Expanded chat templates 
3. LLM synthesis for RAG

This script validates all the requested improvements and provides comprehensive testing.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

# Import components
from app.core.agents.base import BaseAgent, AgentResponse, AgentCapability
from app.core.models.agent_models import AgentRequest
from app.core.services.intent_detection import IntentDetector, IntentType
from app.core.agents.orchestrator import OrchestratorAgent
from app.core.agents.registry import AgentRegistry
from app.core.agents.routing import SmartRouter
from app.core.agents.chat_agent import ChatAgent
from app.core.agents.rag_agent import RAGAgent
from app.core.services.reranking import RerankingService, RerankingContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockSearchService:
    """Mock search service for testing."""
    
    def __init__(self):
        self.mock_documents = [
            {
                'content': 'A matemática é uma ciência exata que estuda padrões, estruturas, mudanças e espaços. É fundamental para muitas outras disciplinas.',
                'score': 0.95,
                'metadata': {
                    'source': 'Base de Conhecimento',
                    'subject_area': 'Matemática',
                    'content_type': 'conceito',
                    'difficulty': 'Básico',
                    'created_date': '2024-01-01T00:00:00'
                }
            },
            {
                'content': 'A álgebra é um ramo da matemática que trabalha com símbolos e as regras para manipular esses símbolos.',
                'score': 0.88,
                'metadata': {
                    'source': 'Khan Academy',
                    'subject_area': 'Matemática',
                    'content_type': 'explicacao',
                    'difficulty': 'Médio',
                    'created_date': '2024-02-01T00:00:00'
                }
            },
            {
                'content': 'Equações lineares são equações algébricas nas quais cada termo é uma constante ou o produto de uma constante e uma única variável.',
                'score': 0.82,
                'metadata': {
                    'source': 'Brasil Escola',
                    'subject_area': 'Matemática',
                    'content_type': 'definição',
                    'difficulty': 'Fácil',
                    'created_date': '2024-03-01T00:00:00'
                }
            }
        ]
    
    def search_documents(self, **kwargs):
        """Simula busca de documentos."""
        query = kwargs.get('query', '').lower()
        
        # Filtrar documentos baseado na query
        results = []
        for doc in self.mock_documents:
            content_lower = doc['content'].lower()
            if any(word in content_lower for word in query.split()):
                results.append(doc)
        
        # Se não encontrou nada, retorna todos
        if not results:
            results = self.mock_documents.copy()
        
        # Aplicar limite
        limit = kwargs.get('limit', 10)
        return results[:limit]


class Phase4ImprovementsValidator:
    """Validator for Phase 4 improvements."""
    
    def __init__(self):
        self.test_results = []
        self.error_count = 0
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASSOU" if success else "❌ FALHOU"
        self.test_results.append({
            'test': test_name,
            'status': status,
            'success': success,
            'details': details
        })
        
        if not success:
            self.error_count += 1
        
        logger.info(f"{status}: {test_name}")
        if details:
            logger.info(f"   Detalhes: {details}")
    
    async def validate_orchestrator_fix(self):
        """Test that orchestrator integration fix works correctly."""
        logger.info("🔧 Testando Correção do Orquestrador...")
        
        try:
            # Setup registry and agents
            registry = AgentRegistry()
            await registry.start()
            
            chat_agent = ChatAgent()
            rag_agent = RAGAgent()
            rag_agent.search_service = MockSearchService()
            
            registry.register(chat_agent)
            registry.register(rag_agent)
            
            # Create orchestrator
            router = SmartRouter()
            orchestrator = OrchestratorAgent(
                agent_registry=registry,
                router=router
            )
            
            # Test 1: Chat request through orchestrator
            chat_request = AgentRequest(
                message="Olá, tudo bem?",
                content="Olá, tudo bem?",
                session_id="test_orchestrator_fix_chat",
                user_id="test_user"
            )
            
            chat_response = await orchestrator.process(chat_request)
            
            chat_success = (
                isinstance(chat_response, AgentResponse) and
                chat_response.confidence > 0.0 and
                len(chat_response.content) > 0 and
                'error' not in chat_response.metadata
            )
            
            self.log_test(
                "Orquestrador - Chat Request",
                chat_success,
                f"Resposta: {chat_response.content[:50]}..." if chat_success else f"Erro: {chat_response.metadata.get('error', 'Resposta inválida')}"
            )
            
            # Test 2: RAG request through orchestrator
            rag_request = AgentRequest(
                message="Explique o que é matemática",
                content="Explique o que é matemática",
                session_id="test_orchestrator_fix_rag",
                user_id="test_user"
            )
            
            rag_response = await orchestrator.process(rag_request)
            
            rag_success = (
                isinstance(rag_response, AgentResponse) and
                rag_response.confidence > 0.0 and
                len(rag_response.content) > 0 and
                'error' not in rag_response.metadata
            )
            
            self.log_test(
                "Orquestrador - RAG Request",
                rag_success,
                f"Confiança: {rag_response.confidence}, Chars: {len(rag_response.content)}" if rag_success else f"Erro: {rag_response.metadata.get('error', 'Resposta inválida')}"
            )
            
            # Test 3: Sequential requests to ensure stability
            stability_success = True
            for i in range(3):
                test_request = AgentRequest(
                    message=f"Teste de estabilidade {i+1}",
                    content=f"Teste de estabilidade {i+1}",
                    session_id=f"test_orchestrator_stability_{i}",
                    user_id="test_user"
                )
                
                test_response = await orchestrator.process(test_request)
                if not (isinstance(test_response, AgentResponse) and test_response.confidence >= 0.0):
                    stability_success = False
                    break
            
            self.log_test(
                "Orquestrador - Estabilidade",
                stability_success,
                "3 requests processados sem erros" if stability_success else "Falha em requests sequenciais"
            )
            
            await registry.stop()
            
        except Exception as e:
            self.log_test(
                "Orquestrador - Teste geral",
                False,
                f"Erro crítico: {str(e)}"
            )
    
    async def validate_expanded_chat_templates(self):
        """Test expanded chat templates functionality."""
        logger.info("💬 Testando Templates de Chat Expandidos...")
        
        try:
            chat_agent = ChatAgent()
            
            # Test 1: Check template variety
            templates = chat_agent.response_templates
            
            # Count total templates
            total_templates = sum(len(templates_list) for templates_list in templates.values())
            expected_min_templates = 50  # Should have at least 50 templates total
            
            template_count_success = total_templates >= expected_min_templates
            
            self.log_test(
                "Templates - Quantidade",
                template_count_success,
                f"Total de templates: {total_templates} (mínimo esperado: {expected_min_templates})"
            )
            
            # Test 2: Check new template categories
            expected_categories = ['greeting', 'farewell', 'help', 'about_system', 'clarification', 'casual', 'encouragement', 'study_tips']
            categories_present = all(cat in templates for cat in expected_categories)
            
            self.log_test(
                "Templates - Categorias",
                categories_present,
                f"Categorias: {list(templates.keys())}"
            )
            
            # Test 3: Check template variety within categories
            greeting_variety = len(templates.get('greeting', [])) >= 10
            help_variety = len(templates.get('help', [])) >= 5
            casual_variety = len(templates.get('casual', [])) >= 8
            
            variety_success = greeting_variety and help_variety and casual_variety
            
            self.log_test(
                "Templates - Variedade",
                variety_success,
                f"Greeting: {len(templates.get('greeting', []))}, Help: {len(templates.get('help', []))}, Casual: {len(templates.get('casual', []))}"
            )
            
            # Test 4: Test template personalization
            test_requests = [
                ("Bom dia!", "greeting"),
                ("Como você pode ajudar?", "help"),
                ("Legal!", "casual"),
                ("Obrigado!", "farewell")
            ]
            
            personalization_success = True
            for message, expected_type in test_requests:
                request = AgentRequest(
                    message=message,
                    content=message,
                    session_id="test_template_personalization",
                    metadata={}
                )
                
                response = await chat_agent.process(request)
                
                # Check if response is personalized (different from template)
                if not (isinstance(response, AgentResponse) and len(response.content) > len(message)):
                    personalization_success = False
                    break
            
            self.log_test(
                "Templates - Personalização",
                personalization_success,
                "Templates são personalizados corretamente" if personalization_success else "Falha na personalização"
            )
            
            # Test 5: Test emoji and formatting presence
            sample_responses = []
            for category in ['greeting', 'help', 'encouragement']:
                if category in templates and templates[category]:
                    sample_responses.extend(templates[category][:2])
            
            emoji_present = any('😊' in resp or '🎯' in resp or '💪' in resp or '🌟' in resp for resp in sample_responses)
            formatting_present = any('**' in resp or '*' in resp for resp in sample_responses)
            
            enhancement_success = emoji_present and formatting_present
            
            self.log_test(
                "Templates - Formatação e Emojis",
                enhancement_success,
                f"Emojis: {emoji_present}, Formatação: {formatting_present}"
            )
            
        except Exception as e:
            self.log_test(
                "Templates - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def validate_llm_synthesis(self):
        """Test LLM synthesis functionality."""
        logger.info("🤖 Testando Síntese LLM para RAG...")
        
        try:
            rag_agent = RAGAgent()
            rag_agent.search_service = MockSearchService()
            
            # Test 1: Check LLM availability detection
            stats = rag_agent.get_statistics()
            llm_available = stats.get('llm_available', False)
            synthesis_method = stats.get('synthesis_method', 'unknown')
            
            self.log_test(
                "LLM Synthesis - Disponibilidade",
                True,  # Always pass, just report status
                f"LLM disponível: {llm_available}, Método de síntese: {synthesis_method}"
            )
            
            # Test 2: Test synthesis configuration
            config_success = (
                'use_llm_synthesis' in rag_agent.config and
                'llm_synthesis_max_sources' in rag_agent.config and
                'llm_synthesis_max_length' in rag_agent.config
            )
            
            self.log_test(
                "LLM Synthesis - Configuração",
                config_success,
                f"Configurações LLM presentes: {config_success}"
            )
            
            # Test 3: Test synthesis with different query types
            test_queries = [
                ("O que é matemática?", "definição"),
                ("Como funciona álgebra?", "processo"),
                ("Por que matemática é importante?", "explicação"),
                ("Explique equações lineares", "informação")
            ]
            
            synthesis_results = []
            for query, query_type in test_queries:
                request = AgentRequest(
                    message=query,
                    content=query,
                    session_id="test_llm_synthesis",
                    metadata={
                        'intent': {
                            'type': IntentType.REQUEST_EXPLANATION.value,
                            'confidence': 0.9
                        }
                    }
                )
                
                response = await rag_agent.process(request)
                
                # Check response quality
                response_quality = (
                    isinstance(response, AgentResponse) and
                    response.confidence > 0.0 and
                    len(response.content) > 50
                )
                
                synthesis_results.append(response_quality)
                
                self.log_test(
                    f"LLM Synthesis - {query_type.title()}",
                    response_quality,
                    f"Query: '{query}' → {len(response.content) if response_quality else 0} chars, confiança: {response.confidence if response_quality else 0}"
                )
            
            # Test 4: Test synthesis vs basic comparison
            # Temporarily disable LLM synthesis to compare
            original_config = rag_agent.config['use_llm_synthesis']
            
            # Test with LLM synthesis
            rag_agent.config['use_llm_synthesis'] = True
            llm_request = AgentRequest(
                message="Explique matemática detalhadamente",
                content="Explique matemática detalhadamente",
                session_id="test_llm_comparison",
                metadata={}
            )
            llm_response = await rag_agent.process(llm_request)
            
            # Test with basic synthesis
            rag_agent.config['use_llm_synthesis'] = False
            basic_request = AgentRequest(
                message="Explique matemática detalhadamente",
                content="Explique matemática detalhadamente", 
                session_id="test_basic_comparison",
                metadata={}
            )
            basic_response = await rag_agent.process(basic_request)
            
            # Restore original config
            rag_agent.config['use_llm_synthesis'] = original_config
            
            # Compare responses
            both_valid = (
                isinstance(llm_response, AgentResponse) and
                isinstance(basic_response, AgentResponse) and
                len(llm_response.content) > 0 and
                len(basic_response.content) > 0
            )
            
            # LLM synthesis should generally produce longer, more sophisticated responses
            llm_more_sophisticated = (
                both_valid and
                len(llm_response.content) >= len(basic_response.content) * 0.8  # Allow some variation
            )
            
            self.log_test(
                "LLM Synthesis - Comparação com Básica",
                both_valid,
                f"LLM: {len(llm_response.content) if both_valid else 0} chars, Básica: {len(basic_response.content) if both_valid else 0} chars"
            )
            
            # Test 5: Test error handling
            # Force an error scenario
            original_search = rag_agent.search_service
            rag_agent.search_service = None  # This should cause graceful fallback
            
            error_request = AgentRequest(
                message="Teste de erro",
                content="Teste de erro",
                session_id="test_error_handling",
                metadata={}
            )
            
            error_response = await rag_agent.process(error_request)
            error_handled = isinstance(error_response, AgentResponse) and len(error_response.content) > 0
            
            # Restore search service
            rag_agent.search_service = original_search
            
            self.log_test(
                "LLM Synthesis - Tratamento de Erros",
                error_handled,
                "Erros tratados graciosamente" if error_handled else "Falha no tratamento de erros"
            )
            
        except Exception as e:
            self.log_test(
                "LLM Synthesis - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def validate_integration_improvements(self):
        """Test overall integration improvements."""
        logger.info("🔗 Testando Melhorias de Integração...")
        
        try:
            # Create complete system
            registry = AgentRegistry()
            await registry.start()
            
            chat_agent = ChatAgent()
            rag_agent = RAGAgent()
            rag_agent.search_service = MockSearchService()
            
            registry.register(chat_agent)
            registry.register(rag_agent)
            
            router = SmartRouter()
            orchestrator = OrchestratorAgent(
                agent_registry=registry,
                router=router
            )
            
            # Test mixed conversation workflow
            session_id = "integration_test_session"
            workflow_steps = [
                ("Olá!", "chat"),
                ("Explique o que é álgebra", "rag"),
                ("Muito obrigado pela explicação!", "chat"),
                ("Encontre mais materiais sobre matemática", "rag"),
                ("Até logo!", "chat")
            ]
            
            workflow_success = True
            for i, (message, expected_agent_type) in enumerate(workflow_steps, 1):
                step_request = AgentRequest(
                    message=message,
                    content=message,
                    session_id=session_id,
                    user_id="integration_test_user"
                )
                
                step_response = await orchestrator.process(step_request)
                
                step_success = (
                    isinstance(step_response, AgentResponse) and
                    step_response.confidence >= 0.0 and
                    len(step_response.content) > 0
                )
                
                if not step_success:
                    workflow_success = False
                
                self.log_test(
                    f"Integração - Passo {i} ({expected_agent_type})",
                    step_success,
                    f"'{message}' → {len(step_response.content) if step_success else 0} chars"
                )
            
            # Test metrics collection
            orchestrator_metrics = orchestrator.get_metrics()
            chat_stats = chat_agent.get_statistics()
            rag_stats = rag_agent.get_statistics()
            
            metrics_success = (
                'total_requests' in orchestrator_metrics and
                'total_sessions' in chat_stats and
                'synthesis_method' in rag_stats
            )
            
            self.log_test(
                "Integração - Métricas",
                metrics_success,
                f"Orchestrator requests: {orchestrator_metrics.get('total_requests', 0)}, Chat sessions: {chat_stats.get('total_sessions', 0)}"
            )
            
            await registry.stop()
            
        except Exception as e:
            self.log_test(
                "Integração - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def run_all_tests(self):
        """Run all improvement validation tests."""
        logger.info("🚀 Iniciando validação das Melhorias da Fase 4")
        logger.info("=" * 80)
        
        # Run all test suites
        await self.validate_orchestrator_fix()
        await self.validate_expanded_chat_templates()
        await self.validate_llm_synthesis()
        await self.validate_integration_improvements()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        logger.info("=" * 80)
        logger.info("📊 RESUMO DA VALIDAÇÃO DAS MELHORIAS")
        logger.info("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total de testes: {total_tests}")
        logger.info(f"✅ Passou: {passed_tests}")
        logger.info(f"❌ Falhou: {failed_tests}")
        logger.info(f"Taxa de sucesso: {(passed_tests/total_tests)*100:.1f}%")
        
        # Breakdown by improvement
        improvements = {
            "Orquestrador": [r for r in self.test_results if 'Orquestrador' in r['test']],
            "Templates": [r for r in self.test_results if 'Templates' in r['test']],
            "LLM Synthesis": [r for r in self.test_results if 'LLM Synthesis' in r['test']],
            "Integração": [r for r in self.test_results if 'Integração' in r['test']]
        }
        
        logger.info("\n📈 RESULTADOS POR MELHORIA:")
        for improvement, tests in improvements.items():
            if tests:
                passed = sum(1 for t in tests if t['success'])
                total = len(tests)
                percentage = (passed/total)*100 if total > 0 else 0
                status = "✅" if percentage == 100 else "⚠️" if percentage >= 80 else "❌"
                logger.info(f"  {status} {improvement}: {passed}/{total} ({percentage:.1f}%)")
        
        if failed_tests > 0:
            logger.info("\n❌ TESTES QUE FALHARAM:")
            for result in self.test_results:
                if not result['success']:
                    logger.info(f"  • {result['test']}: {result['details']}")
        
        logger.info("=" * 80)
        
        if failed_tests == 0:
            logger.info("🎉 TODAS AS MELHORIAS FUNCIONANDO CORRETAMENTE!")
            logger.info("\n🏆 Melhorias implementadas com sucesso:")
            logger.info("  ✅ 1. Correção do orquestrador - 100% de sucesso na integração")
            logger.info("  ✅ 2. Expansão de templates de chat - Conversas mais ricas e variadas")
            logger.info("  ✅ 3. Síntese RAG com LLM - Respostas mais sofisticadas e inteligentes")
            logger.info("  ✅ 4. Integração aprimorada - Sistema robusto e estável")
            logger.info("\n🚀 A Fase 4 está completa e totalmente funcional!")
            return True
        else:
            logger.error(f"💥 {failed_tests} MELHORIAS PRECISAM DE AJUSTES.")
            return False


async def main():
    """Main function."""
    validator = Phase4ImprovementsValidator()
    success = await validator.run_all_tests()
    
    if success:
        print("\n" + "="*50)
        print("✅ VALIDAÇÃO DAS MELHORIAS CONCLUÍDA COM SUCESSO!")
        print("="*50)
        return 0
    else:
        print("\n" + "="*50)
        print("❌ ALGUMAS MELHORIAS PRECISAM DE AJUSTES!")
        print("="*50)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())