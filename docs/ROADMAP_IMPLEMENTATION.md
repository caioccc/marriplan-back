# Roadmap de Implementação - Tutoriando

## ✅ Já Implementado
- [x] ETL Pipeline completo
- [x] Embeddings das questões
- [x] Armazenamento triplo (MongoDB, Qdrant, SQLite)
- [x] LLM com thinking (qwen3:8b)
- [x] Sistema de chat básico
- [x] Autenticação e sessões

## 🚧 Próximas Implementações (Por Prioridade)

### Fase 1: RAG e Busca (1-2 semanas)
- [ ] **Search Service** (`app/core/services/search.py`)
  - Busca vetorial no Qdrant
  - Filtros por matéria, dificuldade, prova
  - Ranking e reranking
  
- [ ] **Question Service** (`app/core/services/question.py`)
  - Recuperar questão completa do MongoDB
  - Formatar questão para apresentação
  - Gerenciar histórico de questões vistas

- [ ] **RAG Integration** (`app/core/models/llm/rag.py`)
  - Injetar contexto de questões no chat
  - Decidir quando usar RAG vs resposta direta

### Fase 2: Sistema de Agentes (2-3 semanas)
- [ ] **Intent Detector** (`app/core/agents/intent_detector.py`)
  - Detectar tipo de interação (chat, questão, resposta, explicação)
  - Extrair filtros da linguagem natural
  
- [ ] **Orchestrator Agent** (`app/core/agents/orchestrator.py`)
  - Rotear para agente apropriado
  - Gerenciar contexto entre agentes

- [ ] **Question Agent** (`app/core/agents/question_agent.py`)
  - Buscar questões adequadas
  - Apresentar questão formatada
  - Verificar respostas
  - Fornecer explicações e referências

### Fase 3: Tracking e Personalização (3-4 semanas)
- [ ] **Progress Tracking**
  - Salvar questões respondidas
  - Calcular taxa de acerto por matéria
  - Identificar pontos fracos

- [ ] **Study Plan Agent**
  - Gerar plano de estudos personalizado
  - Recomendar questões baseado em desempenho
  - Ajustar dificuldade dinamicamente

### Fase 4: Multimodal (4-5 semanas)
- [ ] **LLaVA Integration**
  - Processar questões com imagens
  - Cache de análises visuais
  - Fallback para questões sem imagem

## 📋 Checklist de Validação

### ETL está preparado? ✅
- [x] IDs únicos com SHA1
- [x] Metadados completos (exam, year, difficulty)
- [x] Embeddings ricos com contexto
- [x] Links de referência preservados
- [x] Suporte para imagens

### Fluxo de Questões está viável? ✅
- [x] Filtros disponíveis no Qdrant
- [x] Busca semântica + filtros exatos
- [x] Dados completos no MongoDB
- [x] Histórico rastreável no SQLite

### Arquitetura está alinhada? ✅
- [x] Separação clara de responsabilidades
- [x] Camadas bem definidas
- [x] Escalabilidade considerada
- [x] Modularidade mantida

## 🎯 Próximo Passo Imediato

1. Criar `app/core/services/search.py` com busca no Qdrant
2. Criar endpoint `/api/questions/search/` 
3. Integrar busca no fluxo de chat
4. Testar com queries reais