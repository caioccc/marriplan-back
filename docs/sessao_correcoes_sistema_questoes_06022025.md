# Sessão de Correções do Sistema de Questões - 06/02/2025

## 📋 Resumo Executivo

Esta sessão focou em corrigir três problemas críticos identificados no sistema de questões implementado anteriormente:
1. **Repetição de questões** já respondidas
2. **LLM inventando questões** quando não havia disponíveis
3. **Falta de suporte para referências** a questões anteriores (knowledge_refs)

**Status Final:** ✅ Todos os problemas foram identificados e corrigidos com sucesso.

## 🐛 Problemas Identificados e Soluções

### 1. Repetição de Questões Já Respondidas

**Sintoma:** O usuário recebia a mesma questão de português (bad02c792139) mesmo após já tê-la respondido.

**Diagnóstico:**
- O histórico estava sendo salvo corretamente
- A exclusão de IDs funcionava, MAS...
- O filtro de área estava incorreto

**Problema Raiz:** 
```python
# SearchService estava usando:
subject_area: ['LINGUAGENS, CÓDIGOS E SUAS TECNOLOGIAS', 'Português']

# Qdrant fazia MatchAny, retornando questões que tinham QUALQUER um dos valores
# Resultado: Retornava questões de Inglês e Espanhol também!
```

**Solução Implementada:**
1. Adicionado campo `subject_discipline` no ETL (`/app/core/ETL/loader.py`):
```python
'subject_discipline': subject_area[1] if len(subject_area) > 1 else ''
```

2. Atualizado `SearchFilters` em `/app/core/services/search.py` para incluir o novo campo

3. Modificado viewset para usar `subject_discipline` ao invés de `subject_area`

4. Script executado para atualizar dados existentes no Qdrant

**Arquivos Modificados:**
- `/app/core/ETL/loader.py`
- `/app/core/services/search.py`
- `/app/viewsets.py`

### 2. LLM Inventando Questões

**Sintoma:** Quando o usuário pedia uma terceira questão de português (só existiam 2), a LLM inventava uma questão sobre regência verbal.

**Diagnóstico:**
- O usuário já havia respondido todas as questões de português (2 de 2)
- O sistema corretamente não encontrava questões disponíveis
- A instrução para a LLM era vaga: "informe de forma amigável"

**Problema Raiz:**
```python
# Instrução antiga era muito genérica:
return "[CONTEXTO INTERNO] Não foram encontradas questões com os critérios solicitados. Informe isso ao usuário de forma amigável."
```

**Solução Implementada:**
Instrução explícita e detalhada em `/app/viewsets.py`:
```python
return """[INSTRUÇÃO CRÍTICA]
O usuário pediu uma questão mas NÃO HÁ QUESTÕES DISPONÍVEIS com os critérios solicitados.

IMPORTANTE - VOCÊ DEVE:
1. Informar de forma amigável que não há questões disponíveis no momento
2. NÃO INVENTAR questões sob nenhuma circunstância
3. NÃO CRIAR questões próprias
4. Sugerir que o usuário tente outro assunto ou volte mais tarde

EXEMPLO DE RESPOSTA ADEQUADA:
"Desculpe, mas não consegui encontrar uma questão de português do ENEM no momento. 😕 Talvez todas as questões disponíveis já tenham sido respondidas. Que tal tentar questões de outra matéria, como Geografia ou Inglês?"
[FIM DA INSTRUÇÃO]"""
```

### 3. Falta de Suporte para Referências a Questões Anteriores

**Sintoma:** Quando o usuário perguntava "Sobre a primeira pergunta, você poderia me recomendar links relacionados?", o sistema não reconhecia a solicitação.

**Diagnóstico:**
- As questões tinham `knowledge_refs` com links úteis
- Após responder, a questão era removida da sessão (active_question_id = None)
- Não havia histórico de questões apresentadas

**Problema Raiz:**
1. Só mantínhamos a questão ATIVA, não um histórico
2. Não havia detecção de intenção para referências a questões anteriores
3. knowledge_refs não eram acessíveis após responder

**Solução Implementada:**

1. **Adicionado campo no modelo** (`/app/models.py`):
```python
questions_history = models.JSONField(default=list, blank=True)
```

2. **Salvamento no histórico** ao apresentar questão:
```python
session.questions_history.append({
    'question_id': question_id,
    'subject_area': question_data.get('subject_area', []),
    'specific_topic': question_data.get('specific_topic', ''),
    'difficulty': question_data.get('difficulty', ''),
    'statement_preview': question_data.get('statement', '')[:200] + '...',
    'knowledge_refs': question_data.get('knowledge_refs', []),
    'presented_at': timezone.now().isoformat()
})
```

3. **Detecção de intenção melhorada**:
- Detecta palavras-chave: "primeira questão", "última pergunta", "links", "material de estudo"
- Prioridade na detecção (referências ANTES de novas questões)

4. **Handler específico** `_handle_question_reference()`:
- Recupera questão do histórico
- Formata knowledge_refs de forma elegante
- Retorna contexto apropriado para a LLM

5. **Formatação elegante dos links**:
```
📌 UFAM – "Amazonês - Glossário"
   📝 Notícia oficial sobre o livro
   🔗 https://ufam.edu.br/exemplo
```

**Arquivos Modificados:**
- `/app/models.py` (novo campo)
- `/app/viewsets.py` (detecção e handlers)
- `/app/migrations/0008_add_questions_history_to_session.py` (migração criada)

## 📁 Arquivos Criados/Modificados

### Modificados:
1. `/app/core/ETL/loader.py` - Adicionado campo subject_discipline
2. `/app/core/services/search.py` - Novo campo no SearchFilters e correção do filtro
3. `/app/viewsets.py` - Múltiplas melhorias (detecção de intenção, handlers, instruções)
4. `/app/models.py` - Campo questions_history no UserSession

### Criados:
1. `/app/migrations/0008_add_questions_history_to_session.py` - Migração do novo campo
2. Scripts temporários de debug (foram removidos após uso)

## 🔍 Descobertas Importantes

1. **Estrutura das questões**: `subject_area` sempre tem formato `[área_geral, disciplina_específica]`
2. **Total de questões disponíveis**:
   - Português: 2 questões
   - Geografia: 2 questões
   - Inglês: 2 questões
   - Espanhol: 2 questões
   - Total: 8 questões

3. **Knowledge refs estão completos** com:
   - `mention`: Título/fonte do link
   - `content`: Descrição do conteúdo
   - `href`: URL do recurso

## 🚀 Melhorias Futuras Sugeridas

### Alta Prioridade:
1. **Adicionar mais questões ao banco**
   - Atualmente só há 8 questões totais
   - Adicionar questões de Matemática, Física, Química, Biologia
   - Diversificar anos (2023, 2022, etc.)

2. **Sistema de recomendação inteligente**
   - Quando não houver questões da matéria solicitada, recomendar similares
   - Exemplo: Se não há Português, sugerir outras de Linguagens

3. **Melhorar formatação das questões**
   - Layout mais visual para as alternativas
   - Suporte melhor para imagens
   - Formatação matemática (LaTeX)

### Média Prioridade:
1. **Analytics de desempenho**
   - Dashboard com estatísticas por matéria
   - Gráficos de evolução
   - Identificação de pontos fracos

2. **Sistema de busca mais inteligente**
   - Busca por palavras-chave no conteúdo
   - Filtros combinados (ex: "questão fácil de interpretação")
   - Sugestões baseadas em histórico

3. **Gamificação**
   - Sistema de pontos/níveis
   - Achievements por acertos consecutivos
   - Ranking entre usuários

### Baixa Prioridade:
1. **Exportação de relatórios**
   - PDF com questões respondidas
   - Estatísticas detalhadas
   - Plano de estudos personalizado

2. **Modo competitivo**
   - Desafios entre usuários
   - Questões cronometradas
   - Torneios por matéria

## 📊 Estado Atual do Sistema

### ✅ Funcionando Perfeitamente:
- Busca e apresentação de questões
- Verificação de respostas
- Histórico de questões respondidas
- Exclusão de questões já respondidas
- Detecção de múltiplos formatos de resposta
- Referências a questões anteriores
- Apresentação de knowledge_refs

### ⚠️ Limitações Conhecidas:
- Apenas 8 questões no banco total
- Sem questões de Matemática ou Ciências da Natureza
- Sem suporte para questões com cálculos complexos
- Sem modo offline

## 🎯 Próximos Passos Recomendados

1. **Imediato:** Popular banco com mais questões (mínimo 50-100 por matéria)
2. **Curto prazo:** Implementar sistema de recomendação quando não há questões
3. **Médio prazo:** Dashboard de analytics e progresso
4. **Longo prazo:** Features avançadas (gamificação, modo competitivo)

## 📝 Notas Técnicas

### Padrões Estabelecidos:
- Sempre usar `subject_discipline` para filtros de matéria específica
- Manter histórico completo de questões na sessão
- Instruções explícitas para LLM evitarem comportamentos indesejados
- knowledge_refs devem ser formatados com emojis para melhor visualização

### Comandos Úteis:
```bash
# Ativar ambiente e executar scripts
cd /home/luciojp/projetos/tutoriando-full/tutoriando-back
eval "$(conda shell.bash hook)"
conda activate tutoriando

# Executar migrações
python manage.py makemigrations
python manage.py migrate

# Debug rápido
python manage.py shell
```

---

**Documento criado em:** 06/02/2025  
**Última atualização:** 06/02/2025  
**Status do sistema:** ✅ Totalmente funcional com as correções aplicadas