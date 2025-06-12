import httpx
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama

from app.core.constants import LLM_MODEL_NAME

original_client_init = httpx.Client.__init__


# Patch para manter conexões HTTP/2 ativas por mais tempo

def patched_client_init(self, **kwargs):
    # Forçar configurações de keep-alive longas
    if 'limits' not in kwargs:
        kwargs['limits'] = httpx.Limits(
            max_keepalive_connections=10,
            keepalive_expiry=3600 * 4,  # 4 horas
        )
    if 'headers' not in kwargs:
        kwargs['headers'] = {}
    kwargs['headers']['Connection'] = 'keep-alive'

    return original_client_init(self, **kwargs)


# Aplicar patch
httpx.Client.__init__ = patched_client_init


def init_models():
    llm = Ollama(
        model=LLM_MODEL_NAME,
        request_timeout=300.0,
        temperature=0.7,
        # keep_alive=-1,  # Manter modelo carregado indefinidamente
        additional_kwargs={
            "num_ctx": 2048,  # 32768 (opção) porém o Qwen3 suporte até 40k
            "num_thread": 8,  # Threads de processamento
        }
    )

    Settings.llm = llm
    Settings.llm.complete(
        "Olá! 👋 Eu sou o seu assistente virtual do **Marriplan**, aqui para ajudar você a organizar cada detalhe do seu casamento perfeito!\n\n"
                "Você pode me perguntar sobre:\n"
                "- ✅ Checklist pré-casamento (12 meses)\n"
                "- ✅ Configuração de RSVP e confirmação de presença\n"
                "- ✅ Lista de presentes e organização de convidados\n"
                "- ✅ Agenda do dia do casamento\n"
                "- ✅ Dicas de fornecedores, decoração e muito mais!\n\n"
                "**Como posso ajudar você hoje?**  \n"
                "Exemplos:\n\n"
                "- \"Como montar um checklist de 12 meses?\"\n"
                "- \"Preciso de ideias para uma lista de presentes criativa.\"\n"
                "- \"Como criar um formulário de RSVP eficaz?\""
    )


def count_tokens_approximate(text: str) -> int:
    """
    Aproximação simples de contagem de tokens.
    Em produção, use um tokenizer específico do modelo.
    """
    # Aproximação: ~4 caracteres por token para modelos GPT-like
    # Para maior precisão, use tiktoken ou tokenizer específico
    return len(text) // 4 + len(text.split())
