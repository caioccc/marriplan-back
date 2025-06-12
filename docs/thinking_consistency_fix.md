# Fix da Inconsistência do Thinking Bubble

## Problema Identificado

O balão de pensamento ("pensando...") aparecia inconsistentemente devido à **detecção automática de thinking** que às vezes retornava `True` e às vezes `False`, causando:

- **System prompts diferentes** (com/sem instrução de thinking)
- **Parâmetros LLM diferentes** (temperature 0.6 vs 0.7, top_p 0.95 vs 0.8)
- **Comportamento inconsistente** do thinking bubble

## Causa Raiz

A função `detect_thinking_request()` tinha múltiplas regras inconsistentes:
- ✅/❌ Comandos `/think` ou `/no_think`
- ✅/❌ Palavras-chave: "explique", "calcule", "por que", etc.
- ✅/❌ Padrões regex complexos
- ✅/❌ Mensagens > 200 caracteres
- ✅/❌ Mais de 2 pontos de interrogação

## Solução Implementada

**Removida a detecção automática inconsistente** e implementado **thinking sempre habilitado**:

### 1. Chat Messages (app/core/models/llm/chat.py)
```python
# ANTES:
thinking_enabled = detect_thinking_request(request_data.current_message)

# DEPOIS:
thinking_enabled = True  # Sempre habilitado para consistência
```

### 2. Configuração LLM (app/core/models/llm/config.py)
```python
# ANTES:
"temperature": THINKING_TEMPERATURE if thinking_enabled else NON_THINKING_TEMPERATURE,

# DEPOIS:
"temperature": THINKING_TEMPERATURE,  # Sempre usa parâmetros thinking
```

### 3. System Prompt (app/core/models/llm/system.py)
```python
# ANTES:
if thinking_enabled:
    base_content += "...use <think></think>..."

# DEPOIS:
base_content = "...use <think></think>..."  # Sempre inclui instrução
```

## Comportamento Após Fix

✅ **System prompt sempre igual** - Instrução de thinking sempre presente  
✅ **Parâmetros LLM sempre iguais** - Temperature 0.6, top_p 0.95 consistentes  
✅ **Thinking bubble sempre funciona** - Aparece quando LLM usar tags `<think>`  
✅ **Processamento correto** - Tags sempre removidas do conteúdo principal  
✅ **Compatibilidade mantida** - Agentes não foram afetados  

## Teste de Verificação

Execute o script de teste para verificar a consistência:

```bash
python scripts/test_thinking_consistency.py
```

**Resultado esperado:**
- `prepare_chat_messages()` sempre retorna `thinking_enabled = True`
- Parâmetros de configuração sempre iguais
- System prompt sempre igual
- Processamento de thinking funciona corretamente

## Impacto nos Agentes

✅ **Nenhum agente afetado** - Apenas o sistema de chat principal usa essas funções  
✅ **Retrocompatibilidade** - Mensagens antigas continuam funcionando  
✅ **Performance** - Sem impacto negativo na performance  

## Arquivos Modificados

- `app/core/models/llm/chat.py` - Thinking sempre habilitado
- `app/core/models/llm/config.py` - Parâmetros sempre iguais  
- `app/core/models/llm/system.py` - Prompt sempre com thinking
- `scripts/test_thinking_consistency.py` - Novo teste de consistência

## Resultado

🎯 **Problema resolvido:** O balão "pensando..." agora aparece consistentemente sempre que a LLM usar tags `<think></think>`, independente do tipo de mensagem do usuário.