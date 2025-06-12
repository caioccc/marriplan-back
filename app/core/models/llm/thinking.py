import logging
import re
from typing import Tuple

# Palavras-chave que indicam necessidade de thinking
THINKING_KEYWORDS = [
    # Matemática e cálculos
    'calcule', 'calcular', 'quanto é', 'quanto dá', 'quantos', 'quantas',
    'some', 'subtraia', 'multiplique', 'divida', 'porcentagem', '%',
    'equação', 'fórmula', 'matemática', 'número', 'total',

    # Raciocínio lógico
    'explique', 'por que', 'por quê', 'como', 'analise', 'compare',
    'diferença entre', 'semelhança', 'relação', 'conclusão',
    'deduza', 'infira', 'argumente', 'justifique', 'prove',

    # Questões de concurso/vestibular
    'questão', 'prova', 'concurso', 'enem', 'vestibular', 'alternativa',
    'correta', 'incorreta', 'verdadeiro ou falso', 'certo ou errado',
    'assinale', 'marque', 'escolha', 'responda',

    # Problemas complexos
    'resolva', 'solucione', 'problema', 'exercício', 'desafio',
    'passo a passo', 'etapas', 'procedimento', 'método',

    # Análise profunda
    'detalhe', 'detalhadamente', 'profundamente', 'minuciosamente',
    'passo a passo', 'etapa por etapa', 'explique como'
]

# Padrões de perguntas complexas
COMPLEX_PATTERNS = [
    r'\d+\s*[\+\-\*\/]\s*\d+',  # Operações matemáticas
    r'se\s+.+\s+então',  # Condicionais
    r'dado\s+que',  # Premissas
    r'considerando\s+que',  # Análise contextual
    r'supondo\s+que',  # Hipóteses
]


def detect_thinking_request(message: str) -> bool:
    """Detecta automaticamente quando usar thinking ou respeita comandos manuais."""
    if '/think' in message:
        return True
    elif '/no_think' in message:
        return False

    message_lower = message.lower()

    for keyword in THINKING_KEYWORDS:
        if keyword in message_lower:
            logging.info(f"Thinking automático ativado por palavra-chave: '{keyword}'")
            return True

    for pattern in COMPLEX_PATTERNS:
        if re.search(pattern, message_lower):
            logging.info(f"Thinking automático ativado por padrão: '{pattern}'")
            return True

    if len(message) > 200 or message.count('?') > 2:
        logging.info("Thinking automático ativado por complexidade da mensagem")
        return True

    return False


def parse_thinking_response(response_text: str):
    """Separa thinking content da resposta final."""
    thinking_pattern = r'<think>(.*?)</think>'
    thinking_match = re.search(thinking_pattern, response_text, re.DOTALL)

    if thinking_match:
        thinking_content = thinking_match.group(1).strip()
        final_response = re.sub(thinking_pattern, '', response_text, flags=re.DOTALL).strip()
        return {
            'thinking': thinking_content,
            'response': final_response,
            'has_thinking': True
        }

    return {
        'thinking': '',
        'response': response_text,
        'has_thinking': False
    }


def process_thinking_response(full_content: str) -> tuple[str, str]:
    """Processa resposta com thinking e retorna thinking e resposta separados."""
    parsed = parse_thinking_response(full_content)
    return parsed['thinking'], parsed['response']
