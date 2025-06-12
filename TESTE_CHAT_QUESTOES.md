# 🧪 Guia de Teste do Sistema de Questões no Chat

## 📋 Checklist Pré-Teste

### 1. Serviços Necessários

#### Qdrant (Banco Vetorial)
```bash
# Terminal 1 - Iniciar Qdrant
docker run -p 6333:6333 -v ./qdrant_storage:/qdrant/storage qdrant/qdrant
```

#### Ollama (LLM)
```bash
# Terminal 2 - Verificar se Ollama está rodando
ollama list

# Se não tiver o modelo qwen3:8b, baixar:
ollama pull qwen3:8b
```

#### Backend Django
```bash
# Terminal 3 - Ativar ambiente e rodar backend
conda activate marriplan
python manage.py runserver
```

### 2. Verificar Dados

```bash
# Verificar se há questões no banco
python scripts/inspect_qdrant.py
```

## 🎯 Cenários de Teste

### Teste 1: Pedir uma Questão Simples
```
"Quero uma questão de português"
```

**Esperado:**
- O sistema deve buscar e apresentar uma questão de português
- A questão virá formatada com enunciado e alternativas

### Teste 2: Pedir Questão com Filtros
```
"Me dê uma questão fácil de geografia do ENEM"
```

**Esperado:**
- Questão de Geografia
- Dificuldade: Fácil
- Prova: ENEM

### Teste 3: Responder uma Questão
```
"A resposta é B"
```

**Esperado:**
- Sistema verifica se está correto
- Mostra se acertou ou errou
- Apresenta a resposta correta
- Mostra explicação (se disponível)

### Teste 4: Conversa Normal
```
"Como está o tempo hoje?"
```

**Esperado:**
- Chat responde normalmente, sem buscar questões

## ⚠️ Questões Disponíveis no Banco

Atualmente temos apenas 8 questões do ENEM 2024:
- **Português**: 2 questões
- **Geografia**: 2 questões
- **Inglês**: 2 questões
- **Espanhol**: 2 questões
- **Matemática**: 0 questões ❌

## 🔍 Frases que Ativam Busca de Questões

O sistema detecta pedidos quando encontra palavras como:
- questão / questao
- exercício / exercicio
- problema
- pergunta

## 📝 Exemplos de Interação Completa

### Exemplo 1: Fluxo Completo
```
Você: "Oi, quero uma questão de português do ENEM"
Bot: [Apresenta questão formatada com alternativas]
Você: "A resposta é E"
Bot: "Parabéns! Você acertou! A resposta correta é E. [Explicação...]"
```

### Exemplo 2: Questão Não Disponível
```
Você: "Quero uma questão de matemática"
Bot: "Não encontrei questões com os critérios solicitados."
```

## 🐛 Possíveis Problemas e Soluções

### 1. "Não encontrei questões"
- Verifique se o Qdrant está rodando
- Confirme que o ETL foi executado
- Tente pedir uma área que existe (português, geografia)

### 2. Chat não detecta pedido de questão
- Use palavras-chave claras: "questão", "exercício"
- Seja específico: "Quero uma questão de..."

### 3. Erro ao verificar resposta
- Responda apenas com a letra: "A", "B", "C", "D" ou "E"
- Certifique-se de ter uma questão ativa

## 🎉 Funcionalidades Implementadas

✅ Busca inteligente de questões
✅ Filtros por área, dificuldade e prova
✅ Apresentação formatada das questões
✅ Verificação de respostas
✅ Feedback com explicações
✅ Histórico de questões respondidas
✅ Não repete questões já respondidas

## 🚀 Começar o Teste

1. Certifique-se que todos os serviços estão rodando
2. Acesse o frontend
3. Inicie uma nova sessão de chat
4. Experimente os cenários de teste acima!

Boa sorte com os testes! 🍀