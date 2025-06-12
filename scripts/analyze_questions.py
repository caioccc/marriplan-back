#!/usr/bin/env python
"""
Script para analisar questões específicas no MongoDB.

Uso:
    python scripts/analyze_questions.py
"""

import os
import sys
import django

# Adicionar o diretório pai ao path para importações
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from pymongo import MongoClient
from django.conf import settings
import json

# Conectar ao MongoDB
mongo_client = MongoClient(getattr(settings, 'MONGODB_URL', 'mongodb://localhost:27017/'))
mongo_db = mongo_client[getattr(settings, 'MONGODB_DB', 'marriplan')]
questions_collection = mongo_db['questions']

# IDs das questões a analisar
question_ids = [
    '4e6e7a7cc33b',  # Geografia/Geologia - aparece em busca por "matemática geometria"
    '3429a15eda2f',  # Inglês - segundo resultado
    'bad02c792139',  # Português - quarto resultado
    '15aca0f19359'   # Geografia/Desastre ambiental - terceiro resultado
]

print("=== Análise Detalhada de Questões ===\n")

for qid in question_ids:
    question = questions_collection.find_one({'question_id': qid})

    if question:
        print(f"ID: {qid}")
        print(f"Área: {question.get('subject_area', 'N/A')}")
        print(f"Tópico: {question.get('specific_topic', 'N/A')}")
        print(f"Dificuldade: {question.get('difficulty', 'N/A')}")
        print(f"Keywords: {question.get('keywords', [])}")
        print(f"\nEnunciado:")
        print("-" * 50)
        print(question.get('statement', 'N/A')[:300] + "...")
        print("-" * 50)
        print("\n" + "="*80 + "\n")
    else:
        print(f"Questão {qid} não encontrada no MongoDB\n")

# Análise adicional: buscar questão que deveria aparecer
print("\n=== Verificando se existem questões de Matemática ===\n")

math_questions = questions_collection.find({
    'subject_area': {'$in': ['Matemática', 'MATEMÁTICA E SUAS TECNOLOGIAS']}
}).limit(5)

count = 0
for q in math_questions:
    count += 1
    print(f"- {q['question_id']}: {q.get('specific_topic', 'N/A')}")

if count == 0:
    print("NENHUMA questão de Matemática encontrada no banco!")
else:
    print(f"\nTotal de questões de Matemática encontradas: {count}")