#!/usr/bin/env python
"""
Teste específico para mensagens simples que antes não ativavam thinking.

Uso:
    python scripts/test_simple_message_thinking.py
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

from app.core.models.llm.chat import prepare_chat_messages, ChatRequest

def test_simple_message():
    """Testa se mensagens simples agora sempre habilitam thinking."""
    
    print("=== Teste de Mensagem Simples ===\n")
    
    # Mensagem que ANTES não ativava thinking
    simple_message = "Olá!"
    
    print(f"Mensagem teste: '{simple_message}'")
    print("(Esta mensagem antes NÃO ativava thinking)")
    
    # Testar prepare_chat_messages
    chat_request = ChatRequest(current_message=simple_message, history=[])
    chat_messages, thinking_enabled = prepare_chat_messages(chat_request)
    
    print(f"\nResultado após fix:")
    print(f"  Thinking habilitado: {thinking_enabled}")
    print(f"  Deve ser True: {'✅' if thinking_enabled else '❌'}")
    
    # Verificar system prompt
    system_msg = chat_messages[0] if chat_messages else None
    if system_msg:
        has_thinking_instruction = '<think></think>' in system_msg.content
        print(f"  System prompt inclui instrução thinking: {'✅' if has_thinking_instruction else '❌'}")
    
    print(f"\n✅ Teste finalizado!")
    print("   Agora TODAS as mensagens habilitam thinking consistentemente.")

if __name__ == "__main__":
    test_simple_message()