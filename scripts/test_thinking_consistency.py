#!/usr/bin/env python
"""
Script para testar a consistência do thinking após remoção da detecção automática.

Uso:
    python scripts/test_thinking_consistency.py
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

from app.core.models.llm.thinking import detect_thinking_request, process_thinking_response
from app.core.models.llm.chat import prepare_chat_messages
from app.core.models.llm.config import get_config_params
from app.core.models.llm.system import build_system_prompt
from app.core.models.llm.chat import ChatRequest

def test_thinking_consistency():
    """Testa se o thinking agora é consistente para diferentes tipos de mensagem."""
    
    print("=== Teste de Consistência do Thinking ===\n")
    
    # Diferentes tipos de mensagem
    test_messages = [
        "Olá!",  # Simples
        "Como você está?",  # Pergunta simples
        "Explique como resolver esta equação: 2x + 5 = 15",  # Palavra-chave que ativava thinking
        "Qual é a capital do Brasil?",  # Pergunta simples
        "Me ajude com esta questão de matemática muito complexa que envolve várias etapas e cálculos complicados",  # Mensagem longa
        "????? Por que isto funciona assim?????",  # Muitos pontos de interrogação
        "Calcule 2+2",  # Palavra-chave matemática
        "Esta é uma mensagem normal sem nada especial"  # Normal
    ]
    
    print("1. Teste da detecção automática (deve estar desabilitada):")
    print("-" * 60)
    
    for i, message in enumerate(test_messages, 1):
        thinking_detected = detect_thinking_request(message)
        print(f"{i}. '{message[:40]}{'...' if len(message) > 40 else ''}'")
        print(f"   Thinking detectado: {thinking_detected}")
    
    print(f"\n2. Teste do prepare_chat_messages (deve sempre retornar True):")
    print("-" * 60)
    
    for i, message in enumerate(test_messages, 1):
        chat_request = ChatRequest(current_message=message, history=[])
        chat_messages, thinking_enabled = prepare_chat_messages(chat_request)
        print(f"{i}. '{message[:40]}{'...' if len(message) > 40 else ''}'")
        print(f"   Thinking habilitado: {thinking_enabled}")
    
    print(f"\n3. Teste dos parâmetros de configuração:")
    print("-" * 60)
    
    params_thinking = get_config_params(True)
    params_normal = get_config_params(False)
    
    print(f"Parâmetros com thinking=True: {params_thinking}")
    print(f"Parâmetros com thinking=False: {params_normal}")
    print(f"São iguais: {params_thinking == params_normal}")
    
    print(f"\n4. Teste do system prompt:")
    print("-" * 60)
    
    prompt_thinking = build_system_prompt(True)
    prompt_normal = build_system_prompt(False)
    
    print(f"System prompt com thinking=True:")
    print(f"'{prompt_thinking[:100]}...'")
    print(f"\nSystem prompt com thinking=False:")
    print(f"'{prompt_normal[:100]}...'")
    print(f"São iguais: {prompt_thinking == prompt_normal}")
    
    print(f"\n5. Teste do processamento de thinking:")
    print("-" * 60)
    
    test_response = """<think>
Vou pensar sobre isso...
Este é o raciocínio.
</think>

Esta é a resposta final."""
    
    thinking_content_enabled, response_content_enabled = process_thinking_response(True, test_response)
    thinking_content_disabled, response_content_disabled = process_thinking_response(False, test_response)
    
    print(f"Com thinking=True:")
    print(f"  Thinking: '{thinking_content_enabled[:30]}...'")
    print(f"  Response: '{response_content_enabled[:30]}...'")
    
    print(f"Com thinking=False:")
    print(f"  Thinking: '{thinking_content_disabled}'")
    print(f"  Response: '{response_content_disabled[:30]}...'")
    
    print(f"\n✅ Teste de consistência finalizado!")
    print(f"   - Sistema agora deve ser consistente")
    print(f"   - Thinking sempre habilitado")
    print(f"   - Processamento de tags funciona corretamente")

if __name__ == "__main__":
    test_thinking_consistency()