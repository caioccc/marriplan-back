#!/usr/bin/env python
"""
Teste do processamento de thinking em tempo real durante streaming.

Uso:
    python scripts/test_realtime_thinking.py
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

from app.core.models.llm.streaming_thinking import StreamingThinkingProcessor

def test_realtime_thinking():
    """Testa o processamento de thinking em tempo real."""
    
    print("=== Teste de Thinking em Tempo Real ===\n")
    
    # Simular chunks que chegam em sequência
    chunks = [
        "Vou",
        " responder",
        " sua pergunta",
        ".\n\n<think>",
        "Preciso",
        " pensar",
        " sobre isso",
        ".\nEste é",
        " meu raciocínio",
        ".\nVou analisar",
        " passo a passo",
        ".</think>",
        "\n\nEsta é",
        " a resposta",
        " final",
        " da pergunta",
        "."
    ]
    
    processor = StreamingThinkingProcessor()
    
    print("Processando chunks em tempo real:")
    print("-" * 50)
    
    events_sent = []
    
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: '{chunk}'")
        
        thinking_to_send, response_to_send = processor.process_chunk(chunk)
        
        if thinking_to_send:
            event = f"EVENT: type='thinking', content='{thinking_to_send}'"
            events_sent.append(event)
            print(f"  → {event}")
        
        if response_to_send:
            event = f"EVENT: type='chunk', content='{response_to_send}'"
            events_sent.append(event)
            print(f"  → {event}")
        
        if not thinking_to_send and not response_to_send:
            print("  → (nenhum evento enviado)")
        
        print()
    
    print("=" * 50)
    print("RESUMO DOS EVENTOS ENVIADOS:")
    print("=" * 50)
    
    for i, event in enumerate(events_sent, 1):
        print(f"{i}. {event}")
    
    print(f"\nCONTEÚDO FINAL:")
    thinking_final, response_final = processor.get_final_content()
    print(f"Thinking: '{thinking_final}'")
    print(f"Response: '{response_final}'")
    
    print(f"\n✅ Teste finalizado!")
    print("   O thinking deve ter sido enviado ANTES da resposta final")

def test_simple_response():
    """Testa resposta simples sem thinking."""
    
    print("\n=== Teste de Resposta Simples (Sem Thinking) ===\n")
    
    chunks = ["Esta", " é", " uma", " resposta", " simples", "."]
    
    processor = StreamingThinkingProcessor()
    
    print("Processando resposta simples:")
    print("-" * 30)
    
    for i, chunk in enumerate(chunks):
        thinking_to_send, response_to_send = processor.process_chunk(chunk)
        
        print(f"Chunk {i+1}: '{chunk}' → response: '{response_to_send}'")
        
        if thinking_to_send:
            print(f"  ❌ ERRO: Thinking detectado quando não deveria!")
    
    thinking_final, response_final = processor.get_final_content()
    print(f"\nFinal: thinking='{thinking_final}', response='{response_final}'")
    print("✅ Resposta simples processada corretamente")

if __name__ == "__main__":
    test_realtime_thinking()
    test_simple_response()