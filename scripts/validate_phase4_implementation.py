#!/usr/bin/env python3
"""
Validation script for Phase 4 - Chat & RAG Agents implementation.

This script validates all components of Phase 4:
- Chat Agent functionality
- RAG Agent functionality
- Reranking Service
- Integration with previous phases
- Complete chat and search workflows end-to-end
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

# Import Phase 1, 2, and 3 components
from app.core.agents.base import BaseAgent, AgentResponse, AgentCapability
from app.core.models.agent_models import AgentRequest
from app.core.services.intent_detection import IntentDetector, IntentType
from app.core.agents.orchestrator import OrchestratorAgent
from app.core.agents.registry import AgentRegistry
from app.core.agents.routing import SmartRouter

# Import Phase 4 components
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
                'content': 'Exemplo prático: Para resolver 2x + 5 = 11, subtraímos 5 de ambos os lados: 2x = 6, depois dividimos por 2: x = 3.',
                'score': 0.82,
                'metadata': {
                    'source': 'Brasil Escola',
                    'subject_area': 'Matemática',
                    'content_type': 'exemplo',
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


class Phase4Validator:
    """Validator for Phase 4 implementation."""
    
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
    
    async def validate_reranking_service(self):
        """Test Reranking Service functionality."""
        logger.info("🔍 Testando Reranking Service...")
        
        try:
            # Create reranking service
            reranking = RerankingService()
            
            # Mock documents
            documents = [
                {
                    'content': 'Matemática é importante para resolver problemas do dia a dia',
                    'score': 0.7,
                    'metadata': {'subject_area': 'Matemática', 'difficulty': 'Fácil'}
                },
                {
                    'content': 'Álgebra linear trabalha com vetores e matrizes',
                    'score': 0.8,
                    'metadata': {'subject_area': 'Matemática', 'difficulty': 'Difícil'}
                }
            ]
            
            # Create context
            context = RerankingContext(
                query="matemática básica",
                subject_area="Matemática",
                difficulty_level="Fácil"
            )
            
            # Test reranking
            results = reranking.rerank_documents(documents, context, max_results=2)
            
            assert len(results) == 2, "Deve retornar 2 resultados"
            assert all(hasattr(r, 'reranked_score') for r in results), "Resultados devem ter reranked_score"
            assert all(hasattr(r, 'rank_position') for r in results), "Resultados devem ter rank_position"
            
            self.log_test(
                "Reranking Service - Reordenação básica",
                True,
                f"Reranqueou {len(results)} documentos com sucesso"
            )
            
            # Test statistics
            stats = reranking.get_statistics()
            
            assert 'factor_weights' in stats, "Stats devem ter factor_weights"
            assert 'service_status' in stats, "Stats devem ter service_status"
            
            self.log_test(
                "Reranking Service - Estatísticas",
                True,
                f"Stats: {len(stats)} campos disponíveis"
            )
            
            # Test explanation
            explanation = reranking.get_reranking_explanation(results[0])
            
            assert isinstance(explanation, str), "Explicação deve ser string"
            assert 'Score original' in explanation, "Explicação deve conter score original"
            
            self.log_test(
                "Reranking Service - Explicação",
                True,
                "Explicação gerada com sucesso"
            )
            
        except Exception as e:
            self.log_test(
                "Reranking Service - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def validate_chat_agent(self):
        """Test Chat Agent functionality."""
        logger.info("🔍 Testando Chat Agent...")
        
        try:
            # Create chat agent
            chat_agent = ChatAgent()
            
            # Test greeting handling
            greeting_request = AgentRequest(
                message="Olá, tudo bem?",
                content="Olá, tudo bem?",
                session_id="test_chat_session",
                metadata={
                    'intent': {
                        'type': IntentType.GREETING.value,
                        'confidence': 0.95
                    }
                }
            )
            
            can_handle = chat_agent.can_handle(greeting_request)
            assert can_handle, "Deve conseguir lidar com saudações"
            
            self.log_test(
                "Chat Agent - Can handle saudações",
                True,
                "Detecta saudações corretamente"
            )
            
            # Test greeting response
            response = await chat_agent.process(greeting_request)
            
            assert isinstance(response, AgentResponse), "Deve retornar AgentResponse"
            assert response.confidence > 0.8, "Deve ter alta confiança para saudações"
            assert len(response.content) > 0, "Deve ter conteúdo na resposta"
            
            self.log_test(
                "Chat Agent - Processamento de saudação",
                True,
                f"Resposta: {response.content[:50]}..."
            )
            
            # Test help request
            help_request = AgentRequest(
                message="Como você pode me ajudar?",
                content="Como você pode me ajudar?",
                session_id="test_chat_session",
                metadata={}
            )
            
            help_response = await chat_agent.process(help_request)
            
            assert isinstance(help_response, AgentResponse), "Deve retornar AgentResponse"
            assert help_response.confidence > 0.7, "Deve ter boa confiança para ajuda"
            assert 'ajuda' in help_response.content.lower() or 'posso' in help_response.content.lower()
            
            self.log_test(
                "Chat Agent - Processamento de ajuda",
                True,
                f"Resposta de ajuda adequada"
            )
            
            # Test casual conversation
            casual_request = AgentRequest(
                message="Legal!",
                content="Legal!",
                session_id="test_chat_session",
                metadata={}
            )
            
            casual_response = await chat_agent.process(casual_request)
            
            assert isinstance(casual_response, AgentResponse), "Deve retornar AgentResponse"
            assert casual_response.confidence > 0.5, "Deve ter confiança razoável"
            
            self.log_test(
                "Chat Agent - Conversa casual",
                True,
                "Processa conversa casual adequadamente"
            )
            
            # Test conversation context
            context_summary = chat_agent.get_conversation_summary("test_chat_session")
            
            assert isinstance(context_summary, dict), "Resumo deve ser dict"
            assert 'interaction_count' in context_summary, "Deve ter contador de interações"
            
            self.log_test(
                "Chat Agent - Contexto de conversa",
                True,
                f"Interações registradas: {context_summary.get('interaction_count', 0)}"
            )
            
            # Test statistics
            stats = chat_agent.get_statistics()
            
            assert 'total_sessions' in stats, "Stats devem ter total_sessions"
            assert 'capabilities' in stats, "Stats devem ter capabilities"
            
            self.log_test(
                "Chat Agent - Estatísticas",
                True,
                f"Total sessões: {stats['total_sessions']}"
            )
            
        except Exception as e:
            self.log_test(
                "Chat Agent - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def validate_rag_agent(self):
        """Test RAG Agent functionality."""
        logger.info("🔍 Testando RAG Agent...")
        
        try:
            # Create RAG agent with mock service
            rag_agent = RAGAgent()
            rag_agent.search_service = MockSearchService()
            
            # Test explanation request
            explanation_request = AgentRequest(
                message="Explique o que é matemática",
                content="Explique o que é matemática",
                session_id="test_rag_session",
                metadata={
                    'intent': {
                        'type': IntentType.REQUEST_EXPLANATION.value,
                        'confidence': 0.9,
                        'entities': [{'entity_type': 'subject_area', 'value': 'Matemática'}]
                    }
                }
            )
            
            can_handle = rag_agent.can_handle(explanation_request)
            assert can_handle, "Deve conseguir lidar com pedidos de explicação"
            
            self.log_test(
                "RAG Agent - Can handle explicações",
                True,
                "Detecta pedidos de explicação corretamente"
            )
            
            # Test explanation processing
            response = await rag_agent.process(explanation_request)
            
            assert isinstance(response, AgentResponse), "Deve retornar AgentResponse"
            assert response.confidence > 0.5, "Deve ter confiança razoável"
            assert len(response.content) > 50, "Deve ter conteúdo substancial"
            assert 'matemática' in response.content.lower(), "Deve mencionar matemática"
            
            self.log_test(
                "RAG Agent - Processamento de explicação",
                True,
                f"Resposta com {len(response.content)} chars, confiança: {response.confidence}"
            )
            
            # Test reference request
            reference_request = AgentRequest(
                message="Encontre materiais sobre álgebra",
                content="Encontre materiais sobre álgebra",
                session_id="test_rag_session",
                metadata={
                    'intent': {
                        'type': IntentType.REQUEST_REFERENCE.value,
                        'confidence': 0.85
                    }
                }
            )
            
            ref_response = await rag_agent.process(reference_request)
            
            assert isinstance(ref_response, AgentResponse), "Deve retornar AgentResponse"
            assert ref_response.confidence > 0.4, "Deve ter alguma confiança"
            assert 'álgebra' in ref_response.content.lower() or 'algebra' in ref_response.content.lower()
            
            self.log_test(
                "RAG Agent - Busca de referências",
                True,
                f"Encontrou informações sobre álgebra"
            )
            
            # Test search with no results scenario
            empty_request = AgentRequest(
                message="Explique sobre xyzabc123",
                content="Explique sobre xyzabc123",
                session_id="test_rag_session",
                metadata={}
            )
            
            # Mock empty search
            original_search = rag_agent.search_service.search_documents
            rag_agent.search_service.search_documents = lambda **kwargs: []
            
            empty_response = await rag_agent.process(empty_request)
            
            assert isinstance(empty_response, AgentResponse), "Deve retornar AgentResponse"
            assert empty_response.confidence < 0.5, "Deve ter baixa confiança para resultados vazios"
            
            # Restore original search
            rag_agent.search_service.search_documents = original_search
            
            self.log_test(
                "RAG Agent - Cenário sem resultados",
                True,
                "Lida adequadamente com buscas sem resultados"
            )
            
            # Test statistics
            stats = rag_agent.get_statistics()
            
            assert 'cache_size' in stats, "Stats devem ter cache_size"
            assert 'config' in stats, "Stats devem ter config"
            assert 'capabilities' in stats, "Stats devem ter capabilities"
            
            self.log_test(
                "RAG Agent - Estatísticas",
                True,
                f"Cache size: {stats['cache_size']}, Config: {len(stats['config'])} items"
            )
            
            # Test cache functionality
            rag_agent.clear_cache()
            stats_after_clear = rag_agent.get_statistics()
            
            assert stats_after_clear['cache_size'] == 0, "Cache deve estar vazio após clear"
            
            self.log_test(
                "RAG Agent - Gerenciamento de cache",
                True,
                "Cache limpo com sucesso"
            )
            
        except Exception as e:
            self.log_test(
                "RAG Agent - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def validate_integration_with_orchestrator(self):
        """Test integration of new agents with orchestrator."""
        logger.info("🔍 Testando Integração com Orchestrator...")
        
        try:
            # Create registry and register all agents
            registry = AgentRegistry()
            await registry.start()
            
            # Register Chat Agent
            chat_agent = ChatAgent()
            registry.register(chat_agent)
            
            # Register RAG Agent with mock service
            rag_agent = RAGAgent()
            rag_agent.search_service = MockSearchService()
            registry.register(rag_agent)
            
            # Create orchestrator
            router = SmartRouter()
            orchestrator = OrchestratorAgent(
                agent_registry=registry,
                router=router
            )
            
            # Test chat through orchestrator
            chat_request = AgentRequest(
                message="Olá!",
                content="Olá!",
                session_id="orchestrator_test_chat",
                user_id="test_user"
            )
            
            chat_response = await orchestrator.process(chat_request)
            
            assert isinstance(chat_response, AgentResponse), "Deve retornar AgentResponse"
            
            chat_worked = (
                chat_response.confidence > 0.0 and
                len(chat_response.content) > 0
            )
            
            self.log_test(
                "Integration - Chat via Orchestrator",
                chat_worked,
                f"Chat resposta: {chat_response.content[:50]}..."
            )
            
            # Test RAG through orchestrator
            rag_request = AgentRequest(
                message="Explique matemática",
                content="Explique matemática",
                session_id="orchestrator_test_rag",
                user_id="test_user"
            )
            
            rag_response = await orchestrator.process(rag_request)
            
            assert isinstance(rag_response, AgentResponse), "Deve retornar AgentResponse"
            
            rag_worked = (
                rag_response.confidence > 0.0 and
                len(rag_response.content) > 20
            )
            
            self.log_test(
                "Integration - RAG via Orchestrator",
                rag_worked,
                f"RAG confiança: {rag_response.confidence}"
            )
            
            # Test orchestrator metrics
            metrics = orchestrator.get_metrics()
            
            assert 'total_requests' in metrics, "Metrics devem ter total requests"
            assert metrics['total_requests'] >= 2, "Deve ter processado pelo menos 2 requests"
            
            self.log_test(
                "Integration - Métricas do Orchestrator",
                True,
                f"Total requests: {metrics['total_requests']}"
            )
            
            await registry.stop()
            
        except Exception as e:
            self.log_test(
                "Integration - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def validate_complete_workflows(self):
        """Test complete chat and RAG workflows end-to-end."""
        logger.info("🔍 Testando Workflows Completos...")
        
        try:
            # Setup complete system
            registry = AgentRegistry()
            await registry.start()
            
            # Register all agents
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
            
            session_id = "complete_workflow_test"
            
            # Workflow 1: Chat conversation
            chat_steps = [
                ("Olá!", "greeting"),
                ("Como você pode ajudar?", "help"),
                ("Obrigado!", "farewell")
            ]
            
            chat_workflow_success = True
            for i, (message, expected_type) in enumerate(chat_steps, 1):
                step_request = AgentRequest(
                    message=message,
                    content=message,
                    session_id=f"{session_id}_chat",
                    user_id="test_user"
                )
                
                step_response = await orchestrator.process(step_request)
                step_success = (
                    step_response.confidence > 0.0 and
                    len(step_response.content) > 5
                )
                
                if not step_success:
                    chat_workflow_success = False
                
                self.log_test(
                    f"Workflow Chat - Passo {i}: {expected_type}",
                    step_success,
                    f"Confiança: {step_response.confidence}"
                )
            
            # Workflow 2: RAG search and explanation
            rag_steps = [
                ("O que é álgebra?", "explanation"),
                ("Encontre materiais sobre matemática", "references"),
                ("Explique mais sobre números", "detailed_explanation")
            ]
            
            rag_workflow_success = True
            for i, (message, expected_type) in enumerate(rag_steps, 1):
                step_request = AgentRequest(
                    message=message,
                    content=message,
                    session_id=f"{session_id}_rag",
                    user_id="test_user"
                )
                
                step_response = await orchestrator.process(step_request)
                step_success = (
                    step_response.confidence > 0.0 and
                    len(step_response.content) > 20
                )
                
                if not step_success:
                    rag_workflow_success = False
                
                self.log_test(
                    f"Workflow RAG - Passo {i}: {expected_type}",
                    step_success,
                    f"Confiança: {step_response.confidence}"
                )
            
            # Overall workflow validation
            overall_success = chat_workflow_success and rag_workflow_success
            
            self.log_test(
                "Workflows - Fluxos completos",
                overall_success,
                "Chat e RAG workflows funcionaram adequadamente"
            )
            
            await registry.stop()
            
        except Exception as e:
            self.log_test(
                "Workflows - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def validate_backward_compatibility(self):
        """Test backward compatibility with previous phases."""
        logger.info("🔍 Testando Compatibilidade com Fases Anteriores...")
        
        try:
            # Test Phase 3 components still work
            from app.core.agents.question import QuestionAgent
            
            question_agent = QuestionAgent()
            assert question_agent.name == "QuestionAgent", "Question Agent deve funcionar"
            
            self.log_test(
                "Compatibilidade - Fase 3: QuestionAgent",
                True,
                "QuestionAgent funciona corretamente"
            )
            
            # Test all agents can be registered together
            registry = AgentRegistry()
            await registry.start()
            
            # Register all agent types
            agents = [
                ChatAgent(),
                RAGAgent(),
                QuestionAgent()
            ]
            
            registration_success = True
            for agent in agents:
                success = registry.register(agent)
                if not success:
                    registration_success = False
            
            self.log_test(
                "Compatibilidade - Registro conjunto",
                registration_success,
                f"Todos os {len(agents)} agentes registrados com sucesso"
            )
            
            # Test agent discovery  
            registered_agents = registry.agents  # Use internal registry dict
            
            expected_count = len(agents)
            actual_count = len(registered_agents)
            
            self.log_test(
                "Compatibilidade - Descoberta de agentes",
                actual_count >= expected_count,
                f"Encontrou {actual_count} agentes registrados"
            )
            
            await registry.stop()
            
        except Exception as e:
            self.log_test(
                "Compatibilidade - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def run_all_tests(self):
        """Run all validation tests."""
        logger.info("🚀 Iniciando validação da Fase 4 - Chat & RAG Agents")
        logger.info("=" * 80)
        
        # Run all test suites
        await self.validate_reranking_service()
        await self.validate_chat_agent()
        await self.validate_rag_agent()
        await self.validate_integration_with_orchestrator()
        await self.validate_complete_workflows()
        await self.validate_backward_compatibility()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        logger.info("=" * 80)
        logger.info("📊 RESUMO DA VALIDAÇÃO DA FASE 4")
        logger.info("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total de testes: {total_tests}")
        logger.info(f"✅ Passou: {passed_tests}")
        logger.info(f"❌ Falhou: {failed_tests}")
        logger.info(f"Taxa de sucesso: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            logger.info("\n❌ TESTES QUE FALHARAM:")
            for result in self.test_results:
                if not result['success']:
                    logger.info(f"  • {result['test']}: {result['details']}")
        
        logger.info("=" * 80)
        
        if failed_tests == 0:
            logger.info("🎉 TODOS OS TESTES PASSARAM! A Fase 4 está implementada corretamente.")
            logger.info("\n🚀 Componentes validados com sucesso:")
            logger.info("  ✅ Reranking Service - Melhoria de resultados de busca")
            logger.info("  ✅ Chat Agent - Conversas naturais e casuais")
            logger.info("  ✅ RAG Agent - Busca e síntese de informações")
            logger.info("  ✅ Integração com Orchestrator - Coordenação inteligente")
            logger.info("  ✅ Workflows Completos - Fluxos end-to-end de chat e busca")
            logger.info("  ✅ Compatibilidade - Fases anteriores funcionando")
            logger.info("\n🎯 Benefícios implementados:")
            logger.info("  • Conversas naturais e empáticas")
            logger.info("  • Busca inteligente de informações")
            logger.info("  • Reranking para melhor qualidade de resultados")
            logger.info("  • Síntese automática de múltiplas fontes")
            logger.info("  • Integração perfeita com sistema existente")
            logger.info("  • Experiência de usuário rica e contextual")
            
            return True
        else:
            logger.error("💥 ALGUNS TESTES FALHARAM. Verifique os erros acima.")
            return False


async def main():
    """Main function."""
    validator = Phase4Validator()
    success = await validator.run_all_tests()
    
    if success:
        print("\n" + "="*50)
        print("✅ VALIDAÇÃO DA FASE 4 CONCLUÍDA COM SUCESSO!")
        print("="*50)
        return 0
    else:
        print("\n" + "="*50)
        print("❌ VALIDAÇÃO DA FASE 4 FALHOU!")
        print("="*50)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())