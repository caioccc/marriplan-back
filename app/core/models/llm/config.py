from typing import Dict

# Thinking Mode Parameters
THINKING_TEMPERATURE = 0.6
THINKING_TOP_P = 0.95
THINKING_TOP_K = 20
THINKING_MIN_P = 0


def get_config_params() -> Dict:
    """Retorna parâmetros de geração para o LLM."""
    return {
        "temperature": THINKING_TEMPERATURE,
        "top_p": THINKING_TOP_P,
        "top_k": THINKING_TOP_K,
        "min_p": THINKING_MIN_P
    }
