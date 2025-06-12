#!/usr/bin/env python
"""
Script para inspecionar os dados no Qdrant.

Uso:
    python scripts/inspect_qdrant.py
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

from qdrant_client import QdrantClient
from collections import Counter
import json

# Conectar ao Qdrant
client = QdrantClient(host='localhost', port=6333)

print("=== Inspeção do Qdrant ===\n")

# 1. Informações da collection
try:
    collection_info = client.get_collection('questions')
    print(f"1. Collection 'questions':")
    print(f"   - Vectors count: {collection_info.vectors_count}")
    print(f"   - Points count: {collection_info.points_count}")
    print(f"   - Vector size: {collection_info.config.params.vectors.size}")
    print(f"   - Distance: {collection_info.config.params.vectors.distance}\n")
except Exception as e:
    print(f"Erro ao acessar collection: {e}\n")
    exit(1)

# 2. Amostra de pontos
print("2. Amostra de 5 pontos:")
sample_results = client.scroll(
    collection_name='questions',
    limit=5,
    with_payload=True,
    with_vectors=False
)[0]

for i, point in enumerate(sample_results, 1):
    print(f"\n   Ponto {i}:")
    print(f"   ID: {point.id}")
    print(f"   Payload:")
    for key, value in point.payload.items():
        print(f"     - {key}: {value}")

# 3. Estatísticas dos metadados
print("\n3. Estatísticas dos metadados:")

# Buscar todos os pontos (até 100 para análise)
all_results = client.scroll(
    collection_name='questions',
    limit=100,
    with_payload=True,
    with_vectors=False
)[0]

# Contar valores únicos
stats = {
    'exam': Counter(),
    'subject_area': Counter(),
    'difficulty': Counter(),
    'year': Counter(),
    'has_images': Counter()
}

for point in all_results:
    payload = point.payload
    
    # Exam
    if 'exam' in payload:
        stats['exam'][payload['exam']] += 1
    
    # Subject area (pode ser lista)
    if 'subject_area' in payload:
        areas = payload['subject_area']
        if isinstance(areas, list):
            for area in areas:
                stats['subject_area'][area] += 1
        else:
            stats['subject_area'][areas] += 1
    
    # Difficulty
    if 'difficulty' in payload:
        stats['difficulty'][payload['difficulty']] += 1
    
    # Year
    if 'year' in payload:
        stats['year'][payload['year']] += 1
    
    # Has images
    if 'has_images' in payload:
        stats['has_images'][payload['has_images']] += 1

# Mostrar estatísticas
for field, counter in stats.items():
    print(f"\n   {field}:")
    for value, count in counter.most_common():
        print(f"     - {value}: {count} questões")

# 4. Teste de busca específica
print("\n4. Teste de busca por filtros exatos:")

# Buscar questões de Matemática
from qdrant_client.models import Filter, FieldCondition, MatchAny

test_filter = Filter(
    must=[
        FieldCondition(
            key="subject_area",
            match=MatchAny(any=["Matemática", "MATEMÁTICA E SUAS TECNOLOGIAS"])
        )
    ]
)

math_results = client.search(
    collection_name='questions',
    query_vector=[0.0] * 384,  # Vetor dummy
    query_filter=test_filter,
    limit=5,
    with_payload=True
)

print(f"\n   Questões com área 'Matemática' ou 'MATEMÁTICA E SUAS TECNOLOGIAS': {len(math_results)} encontradas")

if math_results:
    for result in math_results[:2]:  # Mostrar apenas 2
        print(f"\n   - ID: {result.payload['question_id']}")
        print(f"     Área: {result.payload.get('subject_area', 'N/A')}")
        print(f"     Tópico: {result.payload.get('specific_topic', 'N/A')}")

print("\n=== Fim da inspeção ===")