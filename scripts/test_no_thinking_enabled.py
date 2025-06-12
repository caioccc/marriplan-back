#!/usr/bin/env python
"""
Teste para verificar que o sistema funciona sem thinking_enabled.

Uso:
    python scripts/test_no_thinking_enabled.py
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
from app.core.models.llm.config import get_config_params
from app.core.models.llm.system import build_system_prompt
from app.core.models.llm.thinking import process_thinking_response

def test_no_thinking_enabled():
    """Testa que todas as funções funcionam sem thinking_enabled."""
    
    print("=== Teste Sem thinking_enabled ===\n")
    
    # Teste 1: get_config_params() sem parâmetro
    print("1. Testando get_config_params():")
    try:
        config = get_config_params()
        print(f"   ✅ Funcionou: {config}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Teste 2: build_system_prompt() sem parâmetro
    print("\n2. Testando build_system_prompt():")
    try:
        prompt = build_system_prompt()
        print(f"   ✅ Funcionou: '{prompt[:60]}...'")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Teste 3: process_thinking_response() sem thinking_enabled
    print("\n3. Testando process_thinking_response():")
    try:
        test_content = "<think>Pensamento</think>Resposta"
        thinking, response = process_thinking_response(test_content)
        print(f"   ✅ Funcionou:")
        print(f"      Thinking: '{thinking}'")
        print(f"      Response: '{response}'")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Teste 4: prepare_chat_messages() retorna só as mensagens
    print("\n4. Testando prepare_chat_messages():")
    try:
        chat_request = ChatRequest(current_message="Teste", history=[])
        result = prepare_chat_messages(chat_request)
        print(f"   ✅ Funcionou:")
        print(f"      Tipo do retorno: {type(result)}")
        print(f"      Número de mensagens: {len(result)}")
        print(f"      System prompt presente: {result[0].role.value == 'system' if result else False}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print(f"\n✅ Teste finalizado!")
    print("   Todas as funções devem funcionar sem thinking_enabled")

if __name__ == "__main__":
    test_no_thinking_enabled()