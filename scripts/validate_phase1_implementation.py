#!/usr/bin/env python
"""
Script de validação da implementação da Fase 1 - Infraestrutura Base

Este script testa:
1. Sistema de agentes base
2. Detecção de intenção com embeddings
3. Gerenciamento de contexto e memória
4. Modelos de agentes
"""

import os
import sys
import asyncio
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configura Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from app.core.agents import BaseAgent, AgentResponse, AgentCapability, AgentPriority, AgentRegistry
from app.core.services.intent_detection import IntentDetector, IntentType, IntentEntity
from app.core.context import ContextManager, SessionState, SessionStatus, ConversationMemory
from app.core.models.agent_models import (
    AgentRequest, AgentTask, AgentAction, QuestionSearchCriteria,
    AgentMetrics, AgentCommunication
)


class TestAgent(BaseAgent):
    """Agente de teste para validação"""
    
    async def can_handle(self, context: dict) -> float:
        """Sempre pode processar para teste"""
        return 0.8
    
    async def process(self, context: dict) -> AgentResponse:
        """Processa requisição de teste"""
        return AgentResponse(
            agent_name=self.name,
            success=True,
            confidence=0.9,
            message="Processamento de teste bem-sucedido",
            data={'test': True}
        )


class ValidationSuite:
    """Suite de validação da Fase 1"""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Registra resultado de um teste"""
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        self.results.append(f"{status} - {test_name}")
        if details:
            self.results.append(f"   Detalhes: {details}")
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    async def test_agent_system(self):
        """Testa sistema base de agentes"""
        print("\n🔍 Testando Sistema Base de Agentes...")
        
        try:
            # Testa criação de agente
            agent = TestAgent(
                name="test_agent",
                capabilities={AgentCapability.GENERAL_CHAT},
                priority=AgentPriority.NORMAL
            )
            
            # Testa registro
            registry = AgentRegistry()
            registry.register(agent)
            
            # Verifica registro
            retrieved = registry.get_agent("test_agent")
            assert retrieved is not None
            assert retrieved.name == "test_agent"
            
            # Testa processamento
            response = await agent.process({'test': True})
            assert response.success
            assert response.confidence == 0.9
            
            self.log_result("Sistema de Agentes", True, "Criação, registro e processamento funcionando")
            
        except Exception as e:
            self.log_result("Sistema de Agentes", False, str(e))
    
    def test_intent_detection(self):
        """Testa detecção de intenção"""
        print("\n🔍 Testando Detecção de Intenção...")
        
        try:
            detector = IntentDetector(threshold=0.6)
            
            # Testa diferentes intenções
            test_cases = [
                ("Quero uma questão de matemática", IntentType.REQUEST_QUESTION, ["matemática"]),
                ("A resposta é letra B", IntentType.ANSWER_QUESTION, ["B"]),
                ("Pode explicar melhor?", IntentType.REQUEST_EXPLANATION, []),
                ("Olá, bom dia!", IntentType.GREETING, []),
                ("Me dê um exercício fácil de português do ENEM", IntentType.REQUEST_QUESTION, ["português", "fácil", "ENEM"]),
                ("I want a math question", IntentType.REQUEST_QUESTION, ["matemática"]),  # Teste multilíngue - tradução esperada
            ]
            
            all_passed = True
            for text, expected_type, expected_entities in test_cases:
                intent = detector.detect(text)
                
                if intent.type != expected_type:
                    all_passed = False
                    self.log_result(
                        f"Detecção: '{text}'", 
                        False, 
                        f"Esperado {expected_type.value}, obtido {intent.type.value}"
                    )
                else:
                    # Verifica entidades (simplificado, case-insensitive)
                    entity_values = [e.value.lower() if isinstance(e.value, str) else e.value for e in intent.entities]
                    expected_normalized = [exp.lower() if isinstance(exp, str) else exp for exp in expected_entities]
                    entities_match = all(exp in entity_values for exp in expected_normalized)
                    
                    if not entities_match and expected_entities:
                        self.log_result(
                            f"Entidades: '{text}'",
                            False,
                            f"Esperado {expected_entities}, obtido {entity_values}"
                        )
                    else:
                        self.log_result(f"Detecção: '{text}'", True, f"Confiança: {intent.confidence:.2f}")
            
            # Testa detecção com contexto
            context = {'active_question_id': 'Q123'}
            intent_with_context = detector.detect("D", context)
            assert intent_with_context.type == IntentType.ANSWER_QUESTION
            self.log_result("Detecção com contexto", True, "Detectou resposta com questão ativa")
            
        except Exception as e:
            self.log_result("Detecção de Intenção", False, str(e))
    
    def test_context_management(self):
        """Testa gerenciamento de contexto"""
        print("\n🔍 Testando Gerenciamento de Contexto...")
        
        try:
            # Testa criação de contexto
            manager = ContextManager()
            context = manager.get_or_create_context("session_123", "user_456")
            
            assert context.session_state.session_id == "session_123"
            assert context.session_state.user_id == "user_456"
            assert context.session_state.status == SessionStatus.IDLE
            
            self.log_result("Criação de contexto", True, "Contexto criado corretamente")
            
            # Testa estado de sessão
            session_state = context.session_state
            
            # Inicia questão
            question_state = session_state.start_question("Q789")
            assert session_state.status == SessionStatus.QUESTION_PRESENTED
            assert session_state.active_question is not None
            
            # Responde questão
            session_state.answer_question("B", True)
            assert session_state.status == SessionStatus.ANSWER_GIVEN
            assert session_state.active_question.user_answer == "B"
            assert session_state.active_question.is_correct == True
            
            # Finaliza questão
            session_state.finish_question()
            assert session_state.status == SessionStatus.IDLE
            assert len(session_state.questions_history) == 1
            
            self.log_result("Estado de sessão", True, "Ciclo completo de questão funcionando")
            
            # Testa memória de conversa
            memory = context.conversation_memory
            
            # Adiciona mensagens
            memory.add_entry("user", "Quero uma questão", intent="request_question")
            memory.add_entry("assistant", "Aqui está uma questão de matemática...")
            memory.add_entry("user", "A resposta é B", intent="answer_question")
            
            assert len(memory.entries) == 3
            assert memory.entries[0].intent == "request_question"
            
            # Testa janela de contexto
            context_window = memory.get_context_window(max_tokens=100)
            assert len(context_window) > 0
            
            self.log_result("Memória de conversa", True, "Armazenamento e recuperação funcionando")
            
            # Testa busca na memória
            results = memory.search_entries("questão")
            assert len(results) >= 1
            
            self.log_result("Busca na memória", True, "Busca por palavras-chave funcionando")
            
        except Exception as e:
            self.log_result("Gerenciamento de Contexto", False, str(e))
    
    def test_agent_models(self):
        """Testa modelos de agentes"""
        print("\n🔍 Testando Modelos de Agentes...")
        
        try:
            # Testa AgentRequest
            request = AgentRequest(
                message="Teste de requisição",
                session_id="test_session",
                user_id="test_user"
            )
            assert request.message == "Teste de requisição"
            
            # Testa AgentTask
            task = AgentTask(
                action=AgentAction.SEARCH_QUESTION,
                parameters={'subject': 'matemática'},
                priority=1
            )
            assert task.action == AgentAction.SEARCH_QUESTION
            assert task.should_retry() == True
            
            # Testa QuestionSearchCriteria
            criteria = QuestionSearchCriteria(
                subject_area="português",
                difficulty="Fácil",
                exclude_ids=["Q1", "Q2"]
            )
            assert criteria.subject_area == "português"
            assert len(criteria.exclude_ids) == 2
            
            # Testa AgentMetrics
            metrics = AgentMetrics(agent_name="test_agent")
            metrics.record_request(True, 150)
            metrics.record_request(True, 200)
            metrics.record_request(False, 100)
            
            assert metrics.total_requests == 3
            assert metrics.successful_requests == 2
            assert metrics.get_success_rate() > 0.6
            assert metrics.average_response_time_ms == 150.0
            
            self.log_result("Modelos de Agentes", True, "Todos os modelos funcionando corretamente")
            
            # Testa AgentCommunication
            comm = AgentCommunication(
                from_agent="agent1",
                to_agent="agent2",
                message_type="request",
                content={"action": "test"}
            )
            response = comm.create_response({"result": "success"})
            assert response.from_agent == "agent2"
            assert response.to_agent == "agent1"
            assert response.message_type == "response"
            
            self.log_result("Comunicação entre Agentes", True, "Sistema de mensagens funcionando")
            
        except Exception as e:
            self.log_result("Modelos de Agentes", False, str(e))
    
    def test_integration(self):
        """Testa integração entre componentes"""
        print("\n🔍 Testando Integração entre Componentes...")
        
        try:
            # Cria detector e context manager
            detector = IntentDetector()
            context_manager = ContextManager()
            
            # Simula fluxo completo
            session_id = "integration_test"
            user_id = "test_user"
            
            # 1. Cria contexto
            context = context_manager.get_or_create_context(session_id, user_id)
            
            # 2. Detecta intenção
            message = "Quero uma questão difícil de física"
            intent = detector.detect(message)
            
            # 3. Atualiza contexto
            context_manager.update_context(session_id, message, {
                'type': intent.type.value,
                'confidence': intent.confidence,
                'entities': [{'type': e.entity_type, 'value': e.value} for e in intent.entities]
            })
            
            # 4. Adiciona à memória
            context_manager.add_message_to_memory(
                session_id, 
                "user", 
                message,
                intent=intent.type.value,
                entities=[{'entity_type': e.entity_type, 'value': e.value} for e in intent.entities]
            )
            
            # 5. Verifica integração
            updated_context = context_manager._contexts[session_id]
            assert updated_context.current_intent['type'] == IntentType.REQUEST_QUESTION.value
            assert len(updated_context.conversation_memory.entries) == 1
            
            # 6. Simula processamento de questão
            context.session_state.start_question("Q_FISICA_001")
            
            # 7. Nova mensagem com resposta
            answer_message = "A resposta é alternativa C"
            answer_intent = detector.detect(
                answer_message, 
                {'active_question_id': 'Q_FISICA_001'}
            )
            
            assert answer_intent.type == IntentType.ANSWER_QUESTION
            assert answer_intent.get_entity('answer').value == 'C'
            
            self.log_result("Integração", True, "Fluxo completo funcionando corretamente")
            
        except Exception as e:
            self.log_result("Integração", False, str(e))
    
    async def run_all_tests(self):
        """Executa todos os testes"""
        print("="*60)
        print("🚀 VALIDAÇÃO DA FASE 1 - INFRAESTRUTURA BASE")
        print("="*60)
        
        # Executa testes
        await self.test_agent_system()
        self.test_intent_detection()
        self.test_context_management()
        self.test_agent_models()
        self.test_integration()
        
        # Exibe resultados
        print("\n" + "="*60)
        print("📊 RESULTADOS DOS TESTES")
        print("="*60)
        
        for result in self.results:
            print(result)
        
        print("\n" + "-"*60)
        print(f"Total de testes: {self.passed + self.failed}")
        print(f"✅ Passou: {self.passed}")
        print(f"❌ Falhou: {self.failed}")
        print(f"Taxa de sucesso: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        print("-"*60)
        
        if self.failed == 0:
            print("\n🎉 TODOS OS TESTES PASSARAM! A Fase 1 está implementada corretamente.")
        else:
            print("\n⚠️  Alguns testes falharam. Verifique os detalhes acima.")
        
        return self.failed == 0


async def main():
    """Função principal"""
    suite = ValidationSuite()
    success = await suite.run_all_tests()
    
    # Retorna código de saída apropriado
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())