#!/usr/bin/env python
"""
Script para testar o comportamento do ThinkingBubble no chat.

Uso:
    python scripts/test_thinking_bubble.py
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

from app.core.models.llm.thinking import process_thinking_response

def test_thinking_processing():
    """Testa o processamento de mensagens com thinking tags."""
    
    print("=== Teste de Processamento de Thinking Tags ===\n")
    
    # Caso 1: Mensagem com thinking tags
    test_message = """<think>
Vou analisar esta questão sobre matemática.
Primeiro, preciso identificar os conceitos envolvidos.
Depois, vou aplicar a fórmula apropriada.
</think>

A resposta para sua pergunta de matemática é 42.
Para resolver, utilizei o teorema de Pitágoras."""

    thinking_content, response_content = process_thinking_response(True, test_message)
    
    print("Caso 1: Mensagem com thinking tags")
    print("-" * 40)
    print(f"Thinking content:\n{thinking_content}\n")
    print(f"Response content:\n{response_content}\n")
    
    # Caso 2: Mensagem sem thinking tags
    test_message2 = "Esta é uma resposta simples sem pensamento."
    
    thinking_content2, response_content2 = process_thinking_response(True, test_message2)
    
    print("\nCaso 2: Mensagem sem thinking tags")
    print("-" * 40)
    print(f"Thinking content: {thinking_content2}")
    print(f"Response content: {response_content2}\n")
    
    # Caso 3: Thinking desabilitado
    thinking_content3, response_content3 = process_thinking_response(False, test_message)
    
    print("\nCaso 3: Thinking desabilitado")
    print("-" * 40)
    print(f"Thinking content: {thinking_content3}")
    print(f"Response content (deve incluir tags): {response_content3[:100]}...")

if __name__ == "__main__":
    test_thinking_processing()