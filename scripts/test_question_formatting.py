#!/usr/bin/env python
"""
Teste da formatação de questões para diferentes matérias.

Uso:
    python scripts/test_question_formatting.py
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

from backend.app.viewsets_old import ChatMessageViewSet
from app.core.services.question import QuestionService, QuestionDisplay

def test_area_mappings():
    """Testa o mapeamento de áreas para diferentes matérias."""

    print("=== Teste de Mapeamento de Áreas ===\n")

    viewset = ChatMessageViewSet()

    test_messages = [
        "me dê uma questão de português",
        "quero uma questão de matemática",
        "questão de física por favor",
        "preciso de uma questão de geografia",
        "questão de história",
        "questão de química",
        "questão de biologia",
        "questão de inglês"
    ]

    for message in test_messages:
        print(f"Mensagem: '{message}'")
        filters = viewset._extract_filters(message.lower())

        if 'subject_area' in filters:
            area = filters['subject_area']
            print(f"  ✅ Área detectada: {area}")
            print(f"     - Área geral: {area[0]}")
            if len(area) > 1:
                print(f"     - Disciplina específica: {area[1]}")
            else:
                print(f"     - ⚠️  Sem disciplina específica")
        else:
            print(f"  ❌ Nenhuma área detectada")

        print()

def test_question_formatting():
    """Testa a formatação de questões."""

    print("\n=== Teste de Formatação de Questões ===\n")

    question_service = QuestionService()

    # Criar questões de exemplo para diferentes matérias
    test_questions = [
        {
            'question_id': 'test_pt_001',
            'statement': 'Analise o texto a seguir e responda.',
            'choices': {'A': 'Opção A', 'B': 'Opção B', 'C': 'Opção C', 'D': 'Opção D', 'E': 'Opção E'},
            'subject_area': ['LINGUAGENS, CÓDIGOS E SUAS TECNOLOGIAS', 'Português'],
            'specific_topic': 'Interpretação de texto',
            'difficulty': 'Médio',
            'exam': 'ENEM',
            'year': 2024
        },
        {
            'question_id': 'test_mat_001',
            'statement': 'Calcule o valor de x na equação.',
            'choices': {'A': '1', 'B': '2', 'C': '3', 'D': '4', 'E': '5'},
            'subject_area': ['MATEMÁTICA E SUAS TECNOLOGIAS', 'Matemática'],
            'specific_topic': 'Equações do 2º grau',
            'difficulty': 'Fácil',
            'exam': 'ENEM',
            'year': 2024
        },
        {
            'question_id': 'test_fis_001',
            'statement': 'Uma força atua sobre um corpo.',
            'choices': {'A': '10 N', 'B': '20 N', 'C': '30 N', 'D': '40 N', 'E': '50 N'},
            'subject_area': ['CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS', 'Física'],
            'specific_topic': 'Leis de Newton',
            'difficulty': 'Difícil',
            'exam': 'ENEM',
            'year': 2024
        }
    ]

    for question_data in test_questions:
        print(f"Questão: {question_data['subject_area'][1] if len(question_data['subject_area']) > 1 else question_data['subject_area'][0]}")
        print("-" * 50)

        # Formatar questão
        question_display = question_service.format_question_for_display(question_data)
        formatted_question = question_service.format_question_for_chat(question_display)

        print(formatted_question)
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    test_area_mappings()
    test_question_formatting()