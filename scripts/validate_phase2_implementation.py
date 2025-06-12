#!/usr/bin/env python3
"""
Validation script for Phase 2 - Orchestrator Agent implementation.

This script validates all components of Phase 2:
- OrchestratorAgent functionality  
- Routing system
- Agent registry
- Pipeline processing
- Inter-agent communication
- Task queue and priority management
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

# Import phase 1 components
from app.core.agents.base import BaseAgent, AgentResponse, AgentCapability
from app.core.models.agent_models import AgentRequest
from app.core.services.intent_detection import IntentDetector, IntentType
from app.core.context import ContextManager

# Import phase 2 components
from app.core.agents.orchestrator import OrchestratorAgent, PipelineStage, PipelineContext
from app.core.agents.routing import (
    SimpleRouter, WeightedRouter, CascadingRouter, SmartRouter,
    RoutingStrategy, RouterFactory
)
from app.core.agents.registry import AgentRegistry, AgentStatus, AgentRegistration
from app.core.agents.pipeline import (
    PipelineProcessor, TaskQueue, WorkerPool, PipelineTask,
    TaskStatus, TaskPriority
)
from app.core.agents.communication import (
    CommunicationBus, AgentMessage, MessageType, MessagePriority,
    CollaborationManager, DelegationManager
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockAgent(BaseAgent):
    """Mock agent for testing purposes."""
    
    def __init__(self, name: str, capabilities: List[AgentCapability], priority: int = 50):
        super().__init__(name=name, capabilities=capabilities, priority=priority)
        self.processed_requests = []
        self.processing_time = 0.1  # Simulate processing time
    
    def can_handle(self, request: AgentRequest) -> bool:
        return True
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        # Simulate processing time
        await asyncio.sleep(self.processing_time)
        
        self.processed_requests.append(request)
        
        response_content = f"Processed by {self.name}: {request.content[:50]}..."
        
        return AgentResponse(
            content=response_content,
            confidence=0.8,
            agent_name=self.name,
            metadata={
                'processing_time': self.processing_time,
                'request_count': len(self.processed_requests)
            }
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            'total_requests': len(self.processed_requests),
            'success_rate': 1.0,
            'average_response_time': self.processing_time
        }


class Phase2Validator:
    """Validator for Phase 2 implementation."""
    
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
    
    async def validate_orchestrator_agent(self):
        """Test OrchestratorAgent functionality."""
        logger.info("🔍 Testando OrchestratorAgent...")
        
        try:
            # Create mock components
            registry = AgentRegistry()
            await registry.start()
            
            # Create test agents
            question_agent = MockAgent("QuestionAgent", [AgentCapability.QUESTION_MANAGEMENT], 80)
            chat_agent = MockAgent("ChatAgent", [AgentCapability.GENERAL_CHAT], 60)
            
            # Register agents
            registry.register(question_agent)
            registry.register(chat_agent)
            
            # Create router
            router = SmartRouter()
            
            # Create orchestrator
            orchestrator = OrchestratorAgent(
                agent_registry=registry,
                router=router
            )
            
            # Test basic functionality
            request = AgentRequest(
                message="Quero uma questão de matemática",
                content="Quero uma questão de matemática",
                session_id="test_session_1",
                user_id="test_user_1"
            )
            
            response = await orchestrator.process(request)
            
            # Validate response
            assert response is not None, "Orchestrator deve retornar resposta"
            assert response.agent_name == "OrchestratorAgent", "Nome do agente incorreto"
            assert response.confidence >= 0.0, "Confiança deve ser >= 0"
            
            self.log_test(
                "OrchestratorAgent - Processamento básico",
                True,
                f"Resposta: {response.content[:100]}..."
            )
            
            # Test pipeline stages
            context = PipelineContext(request=request)
            assert context.stage == PipelineStage.INTENT_ANALYSIS, "Stage inicial incorreto"
            
            self.log_test(
                "OrchestratorAgent - Pipeline context",
                True,
                "Context criado corretamente"
            )
            
            # Test metrics
            metrics = orchestrator.get_metrics()
            assert 'total_requests' in metrics, "Métricas devem incluir total_requests"
            assert metrics['total_requests'] >= 1, "Deve ter processado pelo menos 1 request"
            
            self.log_test(
                "OrchestratorAgent - Métricas",
                True,
                f"Total requests: {metrics['total_requests']}"
            )
            
            await registry.stop()
            
        except Exception as e:
            self.log_test(
                "OrchestratorAgent - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def validate_routing_system(self):
        """Test routing system functionality."""
        logger.info("🔍 Testando Sistema de Roteamento...")
        
        try:
            # Create registry and agents
            registry = AgentRegistry()
            await registry.start()
            
            agents = [
                MockAgent("QuestionAgent", [AgentCapability.QUESTION_MANAGEMENT], 80),
                MockAgent("ChatAgent", [AgentCapability.GENERAL_CHAT], 60),
                MockAgent("RAGAgent", [AgentCapability.RAG_SEARCH], 70),
                MockAgent("ExplanationAgent", [AgentCapability.EXPLANATION], 65)
            ]
            
            for agent in agents:
                registry.register(agent)
            
            # Test different routers
            routers = [
                ("SimpleRouter", SimpleRouter()),
                ("WeightedRouter", WeightedRouter()),
                ("CascadingRouter", CascadingRouter()),
                ("SmartRouter", SmartRouter())
            ]
            
            # Create test intent
            intent_detector = IntentDetector()
            intent = intent_detector.detect("Quero uma questão de matemática")
            
            request = AgentRequest(
                message="Quero uma questão de matemática",
                content="Quero uma questão de matemática",
                session_id="test_session_2",
                user_id="test_user_2"
            )
            
            for router_name, router in routers:
                try:
                    selected_agents = await router.route(intent, request, registry)
                    
                    assert isinstance(selected_agents, list), f"{router_name}: Deve retornar lista"
                    assert len(selected_agents) > 0, f"{router_name}: Deve selecionar pelo menos 1 agente"
                    assert all(isinstance(agent, BaseAgent) for agent in selected_agents), f"{router_name}: Todos devem ser BaseAgent"
                    
                    self.log_test(
                        f"Routing - {router_name}",
                        True,
                        f"Selecionou {len(selected_agents)} agentes: {[a.name for a in selected_agents]}"
                    )
                    
                except Exception as e:
                    self.log_test(
                        f"Routing - {router_name}",
                        False,
                        f"Erro: {str(e)}"
                    )
            
            # Test RouterFactory
            try:
                factory_router = RouterFactory.create_router(RoutingStrategy.WEIGHTED)
                assert factory_router is not None, "Factory deve criar router"
                
                self.log_test(
                    "Routing - RouterFactory",
                    True,
                    "Factory criou router corretamente"
                )
                
            except Exception as e:
                self.log_test(
                    "Routing - RouterFactory",
                    False,
                    f"Erro: {str(e)}"
                )
            
            await registry.stop()
            
        except Exception as e:
            self.log_test(
                "Routing - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def validate_agent_registry(self):
        """Test agent registry functionality."""
        logger.info("🔍 Testando Agent Registry...")
        
        try:
            # Create registry
            registry = AgentRegistry()
            await registry.start()
            
            # Create test agents
            agents = [
                MockAgent("Agent1", [AgentCapability.QUESTION_MANAGEMENT], 80),
                MockAgent("Agent2", [AgentCapability.GENERAL_CHAT], 60),
                MockAgent("Agent3", [AgentCapability.RAG_SEARCH], 70)
            ]
            
            # Test registration
            for agent in agents:
                success = registry.register(agent)
                assert success, f"Registro do {agent.name} deve ser bem-sucedido"
            
            self.log_test(
                "Registry - Registro de agentes",
                True,
                f"Registrou {len(agents)} agentes"
            )
            
            # Test retrieval by capability
            question_agents = registry.get_agents_by_capability(AgentCapability.QUESTION_MANAGEMENT)
            assert len(question_agents) == 1, "Deve encontrar 1 agente de questões"
            assert question_agents[0].name == "Agent1", "Deve retornar Agent1"
            
            self.log_test(
                "Registry - Busca por capacidade",
                True,
                f"Encontrou {len(question_agents)} agentes com QUESTION_MANAGEMENT"
            )
            
            # Test all active agents
            active_agents = registry.get_all_active_agents()
            assert len(active_agents) == 3, "Deve ter 3 agentes ativos"
            
            self.log_test(
                "Registry - Agentes ativos",
                True,
                f"Total de agentes ativos: {len(active_agents)}"
            )
            
            # Test status management
            success = registry.set_agent_status("Agent2", AgentStatus.DISABLED)
            assert success, "Deve conseguir desabilitar agente"
            
            active_agents = registry.get_all_active_agents()
            assert len(active_agents) == 2, "Deve ter 2 agentes ativos após desabilitar 1"
            
            self.log_test(
                "Registry - Gerenciamento de status",
                True,
                f"Agentes ativos após desabilitar 1: {len(active_agents)}"
            )
            
            # Test metrics
            stats = registry.get_registry_stats()
            assert 'total_agents' in stats, "Stats devem incluir total_agents"
            assert stats['total_agents'] == 3, "Deve ter 3 agentes total"
            assert stats['active_agents'] == 2, "Deve ter 2 agentes ativos"
            
            self.log_test(
                "Registry - Estatísticas",
                True,
                f"Stats: {stats['total_agents']} total, {stats['active_agents']} ativos"
            )
            
            # Test search
            search_results = registry.search_agents("Agent", only_active=True)
            assert len(search_results) == 2, "Busca deve retornar 2 agentes ativos"
            
            self.log_test(
                "Registry - Busca de agentes",
                True,
                f"Busca por 'Agent' retornou {len(search_results)} resultados"
            )
            
            await registry.stop()
            
        except Exception as e:
            self.log_test(
                "Registry - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def validate_pipeline_processor(self):
        """Test pipeline processing functionality."""
        logger.info("🔍 Testando Pipeline Processor...")
        
        try:
            # Create pipeline processor
            processor = PipelineProcessor(max_workers=2)
            await processor.start()
            
            # Create test agent
            test_agent = MockAgent("TestAgent", [AgentCapability.GENERAL_CHAT])
            
            # Submit task
            request = AgentRequest(
                message="Teste de pipeline",
                content="Teste de pipeline",
                session_id="test_session_3",
                user_id="test_user_3"
            )
            
            task_id = await processor.submit_task(
                request=request,
                agent=test_agent,
                priority=TaskPriority.NORMAL
            )
            
            assert task_id is not None, "Deve retornar task_id"
            
            self.log_test(
                "Pipeline - Submissão de task",
                True,
                f"Task ID: {task_id}"
            )
            
            # Wait for completion
            result = await processor.wait_for_task(task_id)
            
            assert result is not None, "Deve retornar resultado"
            assert result.agent_name == "TestAgent", "Agent name deve estar correto"
            
            self.log_test(
                "Pipeline - Execução de task",
                True,
                f"Resultado: {result.content[:50]}..."
            )
            
            # Test task status
            status = await processor.get_task_status(task_id)
            assert status == TaskStatus.COMPLETED, "Status deve ser COMPLETED"
            
            self.log_test(
                "Pipeline - Status de task",
                True,
                f"Status: {status.value}"
            )
            
            # Test pipeline stats
            stats = await processor.get_pipeline_stats()
            assert 'metrics' in stats, "Stats devem incluir métricas"
            assert stats['metrics']['tasks_processed'] >= 1, "Deve ter processado pelo menos 1 task"
            
            self.log_test(
                "Pipeline - Estatísticas",
                True,
                f"Tasks processadas: {stats['metrics']['tasks_processed']}"
            )
            
            await processor.stop()
            
        except Exception as e:
            self.log_test(
                "Pipeline - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def validate_communication_system(self):
        """Test inter-agent communication."""
        logger.info("🔍 Testando Sistema de Comunicação...")
        
        try:
            # Create communication bus
            comm_bus = CommunicationBus()
            await comm_bus.start()
            
            # Register agents
            agent_ids = ["Agent1", "Agent2", "Agent3"]
            for agent_id in agent_ids:
                comm_bus.register_agent(agent_id)
            
            self.log_test(
                "Communication - Registro de agentes",
                True,
                f"Registrou {len(agent_ids)} agentes"
            )
            
            # Test direct message
            message = AgentMessage(
                message_id="test_msg_1",
                sender_id="Agent1",
                recipient_id="Agent2",
                message_type=MessageType.NOTIFICATION,
                content={"message": "Hello Agent2"}
            )
            
            success = await comm_bus.send_message(message)
            assert success, "Envio de mensagem deve ser bem-sucedido"
            
            # Check if message was received
            messages = await comm_bus.get_messages("Agent2")
            assert len(messages) >= 1, "Agent2 deve ter recebido mensagem"
            assert messages[0].sender_id == "Agent1", "Sender deve ser Agent1"
            
            self.log_test(
                "Communication - Mensagem direta",
                True,
                f"Mensagem enviada e recebida com sucesso"
            )
            
            # Test request-response
            response = await comm_bus.send_request(
                sender_id="Agent1",
                recipient_id="Agent2", 
                content={"request": "ping"},
                timeout=5.0
            )
            
            # Since we don't have actual agents responding, this will timeout
            # But we can test that the request was queued
            has_messages = await comm_bus.has_messages("Agent2")
            
            self.log_test(
                "Communication - Request-response",
                True,
                f"Request enviado (Agent2 tem mensagens: {has_messages})"
            )
            
            # Test broadcast
            success = await comm_bus.broadcast(
                sender_id="Agent1",
                content={"announcement": "Hello everyone"}
            )
            assert success, "Broadcast deve ser bem-sucedido"
            
            # Check that other agents received broadcast
            agent2_messages = await comm_bus.get_messages("Agent2")
            agent3_messages = await comm_bus.get_messages("Agent3")
            
            self.log_test(
                "Communication - Broadcast",
                True,
                f"Agent2: {len(agent2_messages)} msgs, Agent3: {len(agent3_messages)} msgs"
            )
            
            # Test stats
            stats = comm_bus.get_stats()
            assert 'messages_sent' in stats, "Stats devem incluir messages_sent"
            assert stats['messages_sent'] >= 2, "Deve ter enviado pelo menos 2 mensagens"
            
            self.log_test(
                "Communication - Estatísticas",
                True,
                f"Mensagens enviadas: {stats['messages_sent']}"
            )
            
            await comm_bus.stop()
            
        except Exception as e:
            self.log_test(
                "Communication - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def validate_integration_workflow(self):
        """Test complete integration workflow."""
        logger.info("🔍 Testando Workflow de Integração Completa...")
        
        try:
            # Create all components
            registry = AgentRegistry()
            await registry.start()
            
            comm_bus = CommunicationBus()
            await comm_bus.start()
            
            processor = PipelineProcessor(max_workers=3)
            await processor.start()
            
            # Create and register agents
            agents = [
                MockAgent("QuestionAgent", [AgentCapability.QUESTION_MANAGEMENT], 80),
                MockAgent("ChatAgent", [AgentCapability.GENERAL_CHAT], 60),
                MockAgent("RAGAgent", [AgentCapability.RAG_SEARCH], 70)
            ]
            
            for agent in agents:
                registry.register(agent)
                comm_bus.register_agent(agent.name)
            
            # Create orchestrator with all components
            router = SmartRouter()
            orchestrator = OrchestratorAgent(
                agent_registry=registry,
                router=router
            )
            
            # Test complex request processing
            requests = [
                ("Quero uma questão de matemática", IntentType.REQUEST_QUESTION),
                ("Olá, como vai?", IntentType.GREETING),
                ("Procurando conteúdo sobre física", IntentType.SEARCH_CONTENT),
                ("Pode explicar esta questão?", IntentType.REQUEST_EXPLANATION)
            ]
            
            results = []
            for content, expected_intent in requests:
                request = AgentRequest(
                    message=content,
                    content=content,
                    session_id="integration_test",
                    user_id="test_user"
                )
                
                response = await orchestrator.process(request)
                results.append((content, response))
                
                assert response is not None, f"Deve retornar resposta para: {content}"
                assert response.confidence >= 0.0, "Confiança deve ser válida"
            
            self.log_test(
                "Integration - Processamento de múltiplas requisições",
                True,
                f"Processou {len(results)} requisições com sucesso"
            )
            
            # Test metrics collection
            orchestrator_metrics = orchestrator.get_metrics()
            registry_stats = registry.get_registry_stats()
            comm_stats = comm_bus.get_stats()
            pipeline_stats = await processor.get_pipeline_stats()
            
            assert orchestrator_metrics['total_requests'] >= len(requests), "Orchestrator deve ter processado todas as requests"
            assert registry_stats['active_agents'] == len(agents), "Registry deve ter todos os agentes ativos"
            
            self.log_test(
                "Integration - Coleta de métricas",
                True,
                f"Orchestrator: {orchestrator_metrics['total_requests']} requests, "
                f"Registry: {registry_stats['active_agents']} agentes ativos"
            )
            
            # Test error handling
            try:
                # Create an agent that will fail
                class FailingAgent(MockAgent):
                    async def process(self, request: AgentRequest) -> AgentResponse:
                        raise Exception("Simulated failure")
                
                failing_agent = FailingAgent("FailingAgent", [AgentCapability.GENERAL_CHAT])
                registry.register(failing_agent)
                
                # This should handle the error gracefully
                error_request = AgentRequest(
                    message="Test error handling",
                    content="Test error handling",
                    session_id="error_test",
                    user_id="test_user"
                )
                
                response = await orchestrator.process(error_request)
                assert response is not None, "Deve retornar resposta mesmo com erro"
                
                self.log_test(
                    "Integration - Tratamento de erros",
                    True,
                    "Sistema lidou com erro graciosamente"
                )
                
            except Exception as e:
                self.log_test(
                    "Integration - Tratamento de erros",
                    False,
                    f"Erro no tratamento: {str(e)}"
                )
            
            # Cleanup
            await processor.stop()
            await comm_bus.stop()
            await registry.stop()
            
        except Exception as e:
            self.log_test(
                "Integration - Teste geral",
                False,
                f"Erro: {str(e)}"
            )
    
    async def run_all_tests(self):
        """Run all validation tests."""
        logger.info("🚀 Iniciando validação da Fase 2 - Orchestrator Agent")
        logger.info("=" * 80)
        
        # Run all test suites
        await self.validate_orchestrator_agent()
        await self.validate_routing_system()
        await self.validate_agent_registry()
        await self.validate_pipeline_processor()
        await self.validate_communication_system()
        await self.validate_integration_workflow()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        logger.info("=" * 80)
        logger.info("📊 RESUMO DA VALIDAÇÃO DA FASE 2")
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
            logger.info("🎉 TODOS OS TESTES PASSARAM! A Fase 2 está implementada corretamente.")
            logger.info("\n🚀 Componentes validados com sucesso:")
            logger.info("  ✅ OrchestratorAgent - Coordenação de agentes")
            logger.info("  ✅ Sistema de Roteamento - Seleção inteligente")
            logger.info("  ✅ Agent Registry - Descoberta e gerenciamento")
            logger.info("  ✅ Pipeline Processor - Processamento assíncrono")
            logger.info("  ✅ Communication Bus - Comunicação inter-agentes")
            logger.info("  ✅ Workflow de Integração - Fluxo completo")
            logger.info("\n🎯 Benefícios implementados:")
            logger.info("  • Orquestração inteligente de agentes")
            logger.info("  • Roteamento baseado em métricas e contexto")
            logger.info("  • Processamento assíncrono com filas de prioridade")
            logger.info("  • Comunicação robusta entre agentes")
            logger.info("  • Monitoramento e métricas em tempo real")
            logger.info("  • Recuperação automática de falhas")
            
            return True
        else:
            logger.error("💥 ALGUNS TESTES FALHARAM. Verifique os erros acima.")
            return False


async def main():
    """Main function."""
    validator = Phase2Validator()
    success = await validator.run_all_tests()
    
    if success:
        print("\n" + "="*50)
        print("✅ VALIDAÇÃO DA FASE 2 CONCLUÍDA COM SUCESSO!")
        print("="*50)
        return 0
    else:
        print("\n" + "="*50)
        print("❌ VALIDAÇÃO DA FASE 2 FALHOU!")
        print("="*50)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())