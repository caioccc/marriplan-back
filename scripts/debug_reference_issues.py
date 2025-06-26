#!/usr/bin/env python3
"""
Script de Debug - Investigação dos Problemas de Referência
===========================================================

Este script investiga os problemas encontrados no teste de validação:
1. "questão anterior a esta" não encontra knowledge_refs
2. Conteúdo proibido ainda aparece nas respostas
"""

import os
import sys
import django
from datetime import datetime

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.app.viewsets_old import ChatMessageViewSet


class TestSession:
    def __init__(self):
        self.questions_history = [
            {
                'question_id': 'Q1',
                'subject_area': ['LINGUAGENS, CÓDIGOS E SUAS TECNOLOGIAS', 'Português'],
                'specific_topic': 'Interpretação de texto',
                'difficulty': 'Médio',
                'statement_preview': 'Expressões e termos utilizados no Amazonas...',
                'knowledge_refs': [
                    {
                        'mention': 'UFAM – "Amazonês - Glossário"',
                        'content': 'Notícia oficial sobre o livro de Sérgio Freire',
                        'href': 'https://ufam.edu.br/noticias/5918'
                    }
                ],
                'presented_at': datetime.now().isoformat()
            },
            {
                'question_id': 'Q2',
                'subject_area': ['LINGUAGENS, CÓDIGOS E SUAS TECNOLOGIAS', 'Português'],
                'specific_topic': 'Mecanismos estilísticos e linguísticos',
                'difficulty': 'Médio',
                'statement_preview': 'Sempre passo nervoso quando leio minha crônica...',
                'knowledge_refs': [
                    {
                        'mention': 'Toda Matéria – artigo "Coesão referencial"',
                        'content': 'Explica que a reiteração é a repetição de um mesmo item lexical',
                        'href': 'https://www.todamateria.com.br/coesao-referencial/'
                    }
                ],
                'presented_at': datetime.now().isoformat()
            }
        ]
        self.active_question_id = 'Q2'


class MockUser:
    def __init__(self):
        self.id = 1
        self.username = "test_user"


def debug_question_index_detection():
    """Debug da detecção de índice de questão"""

    print("🔍 DEBUG: Detecção de Índice de Questão")
    print("=" * 50)

    viewset = ChatMessageViewSet()
    session = TestSession()

    test_messages = [
        'Me indique um material para estudar sobre essa questão?',
        'E sobre a questão anterior a esta, consegue me passar materiais também?'
    ]

    for msg in test_messages:
        print(f"\n📝 Mensagem: '{msg}'")
        intent = viewset._detect_intent(msg, session)
        print(f"   Intent: {intent}")

        if intent['type'] == 'reference_previous_question':
            question_index = intent.get('question_index')
            print(f"   Índice detectado: {question_index}")

            # Tentar acessar a questão
            try:
                if question_index is not None:
                    question_info = session.questions_history[question_index]
                    print(f"   ✅ Questão encontrada: {question_info['question_id']}")
                    print(f"   Tópico: {question_info['specific_topic']}")
                    print(f"   Knowledge_refs: {len(question_info['knowledge_refs'])}")
                else:
                    print(f"   ❌ Índice é None")
            except IndexError as e:
                print(f"   ❌ Erro de índice: {e}")
                print(f"   Total de questões no histórico: {len(session.questions_history)}")


def debug_response_content():
    """Debug do conteúdo das respostas"""

    print("\n\n🔍 DEBUG: Conteúdo das Respostas")
    print("=" * 50)

    viewset = ChatMessageViewSet()
    session = TestSession()
    mock_user = MockUser()

    test_cases = [
        {
            'message': 'Me indique um material para estudar sobre essa questão?',
            'description': 'Última questão (coesão)'
        },
        {
            'message': 'E sobre a questão anterior a esta, consegue me passar materiais também?',
            'description': 'Questão anterior (Amazonas)'
        }
    ]

    for case in test_cases:
        print(f"\n📝 {case['description']}")
        print(f"   Mensagem: '{case['message']}'")

        intent = viewset._detect_intent(case['message'], session)
        print(f"   Intent: {intent}")

        if intent['type'] == 'reference_previous_question':
            try:
                response = viewset._handle_question_reference(intent, session, mock_user)
                print(f"\n   📄 RESPOSTA COMPLETA:")
                print("   " + "="*40)
                # Mostrar primeiras linhas da resposta
                lines = response.split('\n')[:15]
                for line in lines:
                    print(f"   {line}")
                if len(response.split('\n')) > 15:
                    print("   ...")

                # Análises específicas
                print(f"\n   📊 ANÁLISES:")
                print(f"   - Contém ID: {'ID:' in response}")
                print(f"   - Contém knowledge_refs: {'MATERIAL DE REFERÊNCIA' in response}")
                print(f"   - É instrução crítica: {'INSTRUÇÃO CRÍTICA' in response}")
                print(f"   - Contém Pedro Bial: {'Pedro Bial' in response}")
                print(f"   - Contém Paulo Sá: {'Paulo Sá' in response}")

            except Exception as e:
                print(f"   ❌ Erro: {e}")


def debug_wants_refs_detection():
    """Debug da detecção de wants_refs"""

    print("\n\n🔍 DEBUG: Detecção de wants_refs")
    print("=" * 50)

    viewset = ChatMessageViewSet()
    session = TestSession()

    test_messages = [
        'Me indique um material para estudar sobre essa questão?',
        'E sobre a questão anterior a esta, consegue me passar materiais também?'
    ]

    for msg in test_messages:
        print(f"\n📝 Mensagem: '{msg}'")

        # Palavras que devem ativar wants_refs
        wants_refs_words = ['link', 'referência', 'material', 'estudar', 'recomend']
        found_words = [word for word in wants_refs_words if word in msg.lower()]

        print(f"   Palavras encontradas: {found_words}")

        intent = viewset._detect_intent(msg, session)
        print(f"   wants_refs detectado: {intent.get('wants_refs')}")


def main():
    """Executa debug completo"""

    print("🔧 SCRIPT DE DEBUG - PROBLEMAS DE REFERÊNCIA")
    print("=" * 60)
    print(f"📅 Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    debug_question_index_detection()
    debug_response_content()
    debug_wants_refs_detection()

    print("\n\n🎯 CONCLUSÕES")
    print("=" * 50)
    print("Use as informações acima para identificar onde está o problema.")


if __name__ == "__main__":
    main()