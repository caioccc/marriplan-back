"""
Processamento de thinking em tempo real durante streaming.
"""
import re
from typing import Tuple, Optional


class StreamingThinkingProcessor:
    """Processa thinking em tempo real durante o streaming."""
    
    def __init__(self):
        self.buffer = ""
        self.thinking_content = ""
        self.is_in_thinking = False
        self.thinking_sent = False
        self.response_content = ""
    
    def process_chunk(self, chunk: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Processa um chunk e retorna (thinking_to_send, response_to_send).
        
        Returns:
            tuple: (thinking_content_if_complete, response_chunk_if_any)
                  - thinking_content_if_complete: Content to send as 'thinking' event
                  - response_chunk_if_any: Content to send as 'chunk' event
        """
        self.buffer += chunk
        
        # Se já enviamos o thinking, tudo vai para response
        if self.thinking_sent:
            return None, chunk
        
        # Procurar por início de thinking
        if not self.is_in_thinking and '<think>' in self.buffer:
            self.is_in_thinking = True
            # Extrair parte do chunk atual que está antes do <think>
            chunk_before_think = chunk.split('<think>')[0] if '<think>' in chunk else ''
            
            # Atualizar buffer para começar após <think>
            self.buffer = '<think>' + self.buffer.split('<think>', 1)[1]
            
            # Retornar apenas a parte nova antes do <think>
            return None, chunk_before_think if chunk_before_think else None
        
        # Se estamos dentro do thinking, acumular até encontrar </think>
        if self.is_in_thinking:
            if '</think>' in self.buffer:
                # Extrair conteúdo do thinking
                thinking_match = re.search(r'<think>(.*?)</think>(.*)', self.buffer, re.DOTALL)
                if thinking_match:
                    self.thinking_content = thinking_match.group(1).strip()
                    remaining_content = thinking_match.group(2)
                    
                    # Marcar thinking como enviado
                    self.thinking_sent = True
                    self.is_in_thinking = False
                    
                    return self.thinking_content, remaining_content
            
            # Ainda dentro do thinking, não enviar nada
            return None, None
        
        # Conteúdo normal de resposta
        return None, chunk
    
    def get_final_content(self) -> Tuple[str, str]:
        """Retorna (thinking_content, response_content) final."""
        # Como não acumulamos mais internamente, usar process_thinking_response
        from app.core.models.llm.thinking import process_thinking_response
        return process_thinking_response(self.buffer)