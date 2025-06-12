import json
import logging
import time
from typing import List, Dict, Generator, Optional

from llama_index.core import Settings
from llama_index.core.llms import ChatMessage, MessageRole, ChatResponse
from pydantic import BaseModel, Field

from app.core.models.llm.config import get_config_params
from app.core.models.llm.system import build_system_prompt, ensure_system_prompt
from app.core.models.llm.thinking import detect_thinking_request, process_thinking_response
from app.core.models.llm.streaming_thinking import StreamingThinkingProcessor
from app.core.models.utils import count_tokens_approximate
from app.models import UserSession, ChatMessage as ChatMessageModel


# --- Modelos Pydantic para a Requisição ---
class ChatMessageInput(BaseModel):
    """Define a estrutura de uma mensagem no histórico de entrada."""
    role: str  # Espera-se "user", "assistant", ou "system"
    content: str


class ChatRequest(BaseModel):
    """Define a estrutura do corpo da requisição para o endpoint de chat."""
    current_message: str
    history: List[ChatMessageInput] = Field(default_factory=list)  # O histórico é opcional e pode ser uma lista vazia


class StreamingMetrics:
    """Classe para gerenciar métricas de streaming."""

    def __init__(self):
        self.start_time = time.time()
        self.first_chunk_time: Optional[float] = None
        self.chunk_count = 0
        self.full_content = ""

    def mark_first_chunk(self):
        """Marca o tempo do primeiro chunk."""
        if self.first_chunk_time is None:
            self.first_chunk_time = time.time()

    def add_chunk(self, content: str):
        """Adiciona um chunk ao conteúdo total."""
        self.full_content += content
        self.chunk_count += 1

    def calculate_final_metrics(self) -> Dict:
        """Calcula as métricas finais."""
        total_time = time.time() - self.start_time
        time_to_first_token = (self.first_chunk_time - self.start_time) if self.first_chunk_time else 0
        generation_time = total_time - time_to_first_token
        total_tokens = count_tokens_approximate(self.full_content)
        tokens_per_second = total_tokens / generation_time if generation_time > 0 else 0

        return {
            'total_time': round(total_time, 2),
            'time_to_first_token': round(time_to_first_token, 2),
            'generation_time': round(generation_time, 2),
            'total_tokens': total_tokens,
            'tokens_per_second': round(tokens_per_second, 1),
            'chunk_count': self.chunk_count,
            'response_length': len(self.full_content)
        }


def create_chat_history(request_data: ChatRequest) -> List[ChatMessage]:
    """Converte o histórico de entrada para o formato LlamaIndex ChatMessage."""
    chat_history_for_llm: List[ChatMessage] = []

    # Converte o histórico de entrada para o formato LlamaIndex ChatMessage
    for msg_input in request_data.history:
        role_enum: MessageRole
        if msg_input.role.lower() == "user":
            role_enum = MessageRole.USER
        elif msg_input.role.lower() == "assistant":
            role_enum = MessageRole.ASSISTANT
        elif msg_input.role.lower() == "system":
            role_enum = MessageRole.SYSTEM
        else:
            logging.warning(f"Role desconhecido '{msg_input.role}' no histórico. Usando 'user' como padrão.")
            role_enum = MessageRole.USER  # Default para roles não reconhecidos

        chat_history_for_llm.append(ChatMessage(role=role_enum, content=msg_input.content))

    return chat_history_for_llm


def prepare_chat_messages(request_data: ChatRequest) -> List[ChatMessage]:
    """Prepara todas as mensagens (histórico + mensagem atual) para envio ao LLM."""

    # Converter histórico
    chat_history_for_llm = create_chat_history(request_data)

    # Construir e inserir system prompt
    system_content = build_system_prompt()
    chat_history_for_llm = ensure_system_prompt(chat_history_for_llm, system_content)

    # Adicionar mensagem atual do usuário
    chat_history_for_llm.append(ChatMessage(role=MessageRole.USER, content=request_data.current_message))

    logging.info(f"Total de {len(chat_history_for_llm)} mensagens sendo enviadas.")
    return chat_history_for_llm


def process_streaming_response(chat_messages: List[ChatMessage]) -> str:
    """Processa a resposta do LLM usando streaming e retorna o conteúdo completo."""

    # Criar parâmetros específicos para a chamada
    config_params = get_config_params()

    response_stream = Settings.llm.stream_chat(chat_messages, **config_params)
    full_response_content = ""

    for chunk in response_stream:
        full_response_content += chunk.delta
        # print(chunk.delta, end="", flush=True)

    # print()  # Nova linha após o stream terminar
    return full_response_content


def try_fallback_response(chat_messages: List[ChatMessage]) -> str:
    """Tenta obter resposta usando o método de chat não-streaming como fallback."""
    logging.info("Tentando fallback com chat não-streaming...")
    try:
        fallback_response: ChatResponse = Settings.llm.chat(chat_messages)
        content = fallback_response.message.content

        if not content.strip():
            logging.warning("LLM (chat fallback) também retornou uma resposta vazia ou apenas espaços em branco.")
        else:
            logging.info("Fallback com chat não-streaming obteve uma resposta.")

        return content
    except Exception as fallback_e:
        logging.error(f"Erro na chamada de fallback do LLM (chat): {fallback_e}")
        raise fallback_e


def get_llm_response(chat_messages: List[ChatMessage]) -> Dict[str, str]:
    """Obtém resposta do LLM, tentando streaming primeiro e fallback se necessário."""
    try:
        # Tentar resposta com streaming
        full_response_content = process_streaming_response(chat_messages)

        # Verificar se a resposta está vazia e tentar fallback
        if not full_response_content.strip():
            logging.warning("LLM (stream_chat) retornou uma resposta vazia ou apenas espaços em branco.")
            full_response_content = try_fallback_response(chat_messages)

            # Se ainda estiver vazio após fallback
            if not full_response_content.strip():
                return {"error": "LLM retornou resposta vazia mesmo após fallback"}

        return {"answer": full_response_content}

    except Exception as e:
        logging.error(f"Erro crítico durante a chamada ao LLM: {e}", exc_info=True)
        return {"error": f"Erro ao processar com o LLM: {str(e)}"}


def log_response_metrics(result: Dict[str, str], total_time: float) -> None:
    """Registra métricas e logs da resposta do LLM."""
    if "answer" in result:
        answer_preview = result["answer"][:200] + "..." if len(result["answer"]) > 200 else result["answer"]
        logging.info(f"Resposta do LLM: '{answer_preview}'")

    logging.info(f"Tempo total de processamento da requisição: {total_time:.2f}s")


def process_streaming_chunks(chat_messages: List[ChatMessage], metrics: StreamingMetrics) -> Generator[str, None, None]:
    """Processa chunks de streaming e gera eventos SSE."""
    thinking_processor = StreamingThinkingProcessor()
    
    try:
        # Criar parâmetros específicos para a chamada
        config_params = get_config_params()

        response_stream = Settings.llm.stream_chat(chat_messages, **config_params)

        for chunk in response_stream:
            if chunk.delta:
                metrics.mark_first_chunk()
                metrics.add_chunk(chunk.delta)

                # Processar chunk para detectar thinking em tempo real
                thinking_to_send, response_to_send = thinking_processor.process_chunk(chunk.delta)
                
                # Enviar evento de thinking se disponível
                if thinking_to_send:
                    yield f"data: {json.dumps({'type': 'thinking', 'content': thinking_to_send})}\n\n"
                
                # Enviar chunk de resposta se disponível
                if response_to_send:
                    yield f"data: {json.dumps({'type': 'chunk', 'content': response_to_send})}\n\n"

    except Exception as e:
        logging.error(f"Erro durante streaming: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': f'Erro no streaming: {str(e)}'})}\n\n"


def handle_fallback_streaming(chat_messages: List[ChatMessage], metrics: StreamingMetrics) -> Generator[
    str, None, None]:
    """Trata fallback quando streaming retorna vazio."""
    yield f"data: {json.dumps({'type': 'status', 'message': 'Tentando método alternativo...'})}\n\n"

    fallback_start_time = time.time()
    try:
        fallback_response = Settings.llm.chat(chat_messages)
        fallback_content = fallback_response.message.content

        if fallback_content.strip():
            # Ajustar métricas para fallback
            metrics.first_chunk_time = fallback_start_time
            metrics.add_chunk(fallback_content)
            metrics.chunk_count = 1

            # Processar fallback content para thinking
            thinking_processor = StreamingThinkingProcessor()
            thinking_to_send, response_to_send = thinking_processor.process_chunk(fallback_content)
            
            # Enviar thinking se encontrado
            if thinking_to_send:
                yield f"data: {json.dumps({'type': 'thinking', 'content': thinking_to_send})}\n\n"
            
            # Enviar resposta
            if response_to_send:
                yield f"data: {json.dumps({'type': 'chunk', 'content': response_to_send})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'error', 'message': 'LLM retornou resposta vazia mesmo após fallback'})}\n\n"

    except Exception as fallback_e:
        logging.error(f"Erro na chamada de fallback do LLM: {fallback_e}")
        yield f"data: {json.dumps({'type': 'error', 'message': f'Erro no fallback: {str(fallback_e)}'})}\n\n"


def save_chat_messages(session: UserSession, user_message: str, llm_response: str, thinking_content: str = '') -> None:
    """Salva as mensagens do chat no banco de dados."""
    ChatMessageModel.objects.create(session=session, is_user=True, content=user_message)
    ChatMessageModel.objects.create(
        session=session, 
        is_user=False, 
        content=llm_response,
        thinking_content=thinking_content if thinking_content else None
    )


def log_streaming_metrics(metrics: StreamingMetrics) -> None:
    """Registra logs das métricas de streaming."""
    final_metrics = metrics.calculate_final_metrics()
    logging.info(
        f"Streaming concluído - Tempo total: {final_metrics['total_time']}s, "
        f"TTFT: {final_metrics['time_to_first_token']}s, "
        f"Tokens: {final_metrics['total_tokens']}, "
        f"Tokens/s: {final_metrics['tokens_per_second']}"
    )


def generate_streaming_response(chat_messages: List[ChatMessage],
                                session: UserSession,
                                user_message: str) -> Generator[str, None, None]:
    """Gera resposta de streaming completa com métricas."""

    metrics = StreamingMetrics()
    thinking_processor = StreamingThinkingProcessor()

    try:
        # Processar chunks de streaming
        for chunk_event in process_streaming_chunks(chat_messages, metrics):
            yield chunk_event

        # Verificar se precisa de fallback
        if not metrics.full_content.strip():
            logging.warning("LLM retornou resposta vazia. Tentando fallback...")
            for fallback_event in handle_fallback_streaming(chat_messages, metrics):
                yield fallback_event

            if not metrics.full_content.strip():
                yield f"data: {json.dumps({'type': 'error', 'message': 'LLM retornou resposta vazia mesmo após fallback'})}\n\n"
                return

        # Como thinking já foi processado em tempo real, apenas limpar o conteúdo final
        thinking_content, response_content = process_thinking_response(metrics.full_content)
        
        # Salvar no banco com conteúdo limpo
        save_chat_messages(session, user_message, response_content, thinking_content)
        log_streaming_metrics(metrics)

        # Enviar evento de conclusão
        final_metrics = metrics.calculate_final_metrics()
        yield f"data: {json.dumps({'type': 'done', 'metrics': final_metrics})}\n\n"

    except Exception as e:
        logging.error(f"Erro crítico durante streaming: {e}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': f'Erro ao processar: {str(e)}'})}\n\n"
