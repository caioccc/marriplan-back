#!/usr/bin/env python
"""
Script para testar o fluxo completo do thinking bubble (backend + banco de dados).

Uso:
    python scripts/test_full_thinking_flow.py
"""

import os
import sys

# Adicionar o diretório pai ao path para importações
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from app.models import ChatMessage, UserSession, CustomUser
from app.core.models.llm.thinking import process_thinking_response, detect_thinking_request
from app.core.models.llm.chat import save_chat_messages

def test_thinking_flow():
    """Testa o fluxo completo do thinking."""
    
    print("=== Teste do Fluxo Completo de Thinking ===\n")
    
    # Obter ou criar usuário de teste
    user, created = CustomUser.objects.get_or_create(
        username='test_thinking',
        defaults={'email': 'test@example.com'}
    )
    if created:
        print("✓ Usuário de teste criado")
    
    # Obter ou criar sessão de teste
    session, created = UserSession.objects.get_or_create(
        user=user,
        session_id='test_thinking_session',
        defaults={'title': 'Teste Thinking'}
    )
    if created:
        print("✓ Sessão de teste criada")
    
    # Teste 1: Mensagem que ativa thinking
    test_message = "Explique como resolver esta equação: 2x + 5 = 15"
    
    print(f"\n1. Teste de detecção de thinking:")
    print(f"   Mensagem: '{test_message}'")
    
    thinking_enabled = detect_thinking_request(test_message)
    print(f"   Thinking detectado: {thinking_enabled}")
    
    # Teste 2: Simulação de resposta da LLM com thinking
    llm_response = """<think>
Para resolver esta equação linear:
1. Primeiro, isolo o termo com x
2. Depois, divido ambos os lados
3. Finalmente, encontro o valor de x
</think>

Para resolver a equação 2x + 5 = 15:

1. Subtraio 5 de ambos os lados: 2x = 10
2. Divido ambos os lados por 2: x = 5

A resposta é x = 5."""
    
    print(f"\n2. Teste de processamento da resposta:")
    thinking_content, response_content = process_thinking_response(thinking_enabled, llm_response)
    
    print(f"   Thinking extraído: '{thinking_content[:50]}...'")
    print(f"   Resposta limpa: '{response_content[:50]}...'")
    
    # Teste 3: Salvamento no banco
    print(f"\n3. Teste de salvamento no banco:")
    
    # Limpar mensagens anteriores desta sessão
    ChatMessage.objects.filter(session=session).delete()
    
    save_chat_messages(session, test_message, response_content, thinking_content)
    
    # Verificar se foi salvo corretamente
    messages = ChatMessage.objects.filter(session=session).order_by('created_at')
    
    print(f"   Mensagens salvas: {messages.count()}")
    
    for msg in messages:
        print(f"   - {'Usuário' if msg.is_user else 'IA'}: {msg.content[:30]}...")
        if not msg.is_user and msg.thinking_content:
            print(f"     Thinking: {msg.thinking_content[:30]}...")
    
    # Teste 4: Verificar remoção das tags mesmo com thinking desabilitado
    print(f"\n4. Teste com thinking desabilitado:")
    
    thinking_content_disabled, response_content_disabled = process_thinking_response(False, llm_response)
    
    print(f"   Thinking (deve estar vazio): '{thinking_content_disabled}'")
    print(f"   Resposta (deve estar limpa): '{response_content_disabled[:50]}...'")
    print(f"   Tags removidas: {'<think>' not in response_content_disabled}")
    
    print(f"\n✅ Teste completo finalizado!")

if __name__ == "__main__":
    test_thinking_flow()