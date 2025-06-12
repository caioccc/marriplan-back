# Scripts Utilitários - Marriplan Backend

Esta pasta contém scripts utilitários para manutenção, testes e inspeção do projeto Marriplan.

## 📁 Estrutura

```
scripts/
├── README.md              # Este arquivo
├── inspect_qdrant.py      # Inspeciona dados no Qdrant
├── reset_etl.py          # Limpa e reprocessa ETL
└── test_search_service.py # Testa o SearchService
```

## 🛠️ Scripts Disponíveis

### 1. **inspect_qdrant.py**
Inspeciona os dados armazenados no banco vetorial Qdrant.

```bash
# Executar do diretório raiz do projeto
python scripts/inspect_qdrant.py
```

**Funcionalidades:**
- Mostra informações da collection (vetores, pontos, configurações)
- Exibe amostra de questões armazenadas
- Apresenta estatísticas dos metadados
- Testa buscas com filtros específicos

### 2. **reset_etl.py**
Limpa todos os dados de questões e executa o ETL novamente.

```bash
# Executar do diretório raiz do projeto
python scripts/reset_etl.py
```

**⚠️ ATENÇÃO:** Este script DELETA todos os dados de questões dos três bancos:
- SQLite (QuestionReference)
- MongoDB (questions collection)
- Qdrant (questions collection)

**Funcionalidades:**
- Solicita confirmação antes de executar
- Limpa dados de todos os bancos
- Executa ETL completo novamente
- Útil para reprocessar após mudanças no ETL

### 3. **test_search_service.py**
Testa as funcionalidades do SearchService.

```bash
# Executar do diretório raiz do projeto
python scripts/test_search_service.py
```

**Funcionalidades:**
- Testa busca semântica simples
- Testa busca com filtros complexos
- Testa busca por áreas específicas
- Testa busca de questões similares
- Exibe scores e metadados dos resultados

## 📋 Pré-requisitos

### 1. Ambiente Conda
Todos os scripts devem ser executados no ambiente conda `marriplan`:

```bash
conda activate marriplan
```

### 2. Serviços Necessários

**Para `inspect_qdrant.py` e `test_search_service.py`:**
- Qdrant rodando na porta 6333

```bash
docker run -p 6333:6333 -v ./qdrant_storage:/qdrant/storage qdrant/qdrant
```

**Para `reset_etl.py`:**
- Qdrant rodando
- MongoDB rodando (se configurado)
- Django configurado corretamente

### 3. Django Configurado
Os scripts dependem das configurações do Django. Certifique-se de que:
- As variáveis de ambiente estão configuradas
- O arquivo `backend/settings.py` está correto
- Os modelos do Django estão migrados

## 🔧 Desenvolvimento

### Adicionando Novos Scripts

1. Crie o arquivo na pasta `scripts/`
2. Use o template padrão para configurar Django:

```python
#!/usr/bin/env python
"""
Descrição do script

Uso:
    python scripts/nome_do_script.py
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

# Seu código aqui...
```

3. Atualize este README com a documentação do novo script

## 🐛 Troubleshooting

### Erro: "ModuleNotFoundError"
- Certifique-se de executar do diretório raiz do projeto
- Verifique se o ambiente conda está ativado

### Erro: "Connection refused" (Qdrant)
- Verifique se o Qdrant está rodando
- Confirme a porta (padrão: 6333)

### Erro: "Collection not found"
- Execute o ETL primeiro para criar as collections
- Use `reset_etl.py` se necessário

## 📝 Notas

- Estes scripts são ferramentas de desenvolvimento/manutenção
- Não devem ser executados em produção sem cuidado
- Sempre faça backup antes de usar scripts destrutivos como `reset_etl.py`