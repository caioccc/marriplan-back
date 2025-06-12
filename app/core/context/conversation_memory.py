"""
Gerenciamento de memória da conversa
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json


@dataclass
class MemoryEntry:
    """Entrada individual na memória da conversa"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    intent: Optional[str] = None
    entities: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'intent': self.intent,
            'entities': self.entities,
            'metadata': self.metadata,
            'token_count': self.token_count
        }
    
    def estimate_tokens(self) -> int:
        """Estima número de tokens (aproximado)"""
        # Estimativa simples: ~4 caracteres por token
        self.token_count = len(self.content) // 4
        return self.token_count


class ConversationMemory:
    """Gerencia a memória da conversa com janela deslizante"""
    
    def __init__(self, max_entries: int = 20, max_tokens: int = 4000):
        """
        Inicializa memória da conversa
        
        Args:
            max_entries: Número máximo de entradas a manter
            max_tokens: Número máximo de tokens a manter
        """
        self.max_entries = max_entries
        self.max_tokens = max_tokens
        self.entries: List[MemoryEntry] = []
        self.summary: Optional[str] = None
        self.total_tokens = 0
    
    def add_entry(self, role: str, content: str, intent: Optional[str] = None,
                  entities: Optional[List[Dict]] = None, metadata: Optional[Dict] = None):
        """Adiciona nova entrada à memória"""
        entry = MemoryEntry(
            role=role,
            content=content,
            intent=intent,
            entities=entities or [],
            metadata=metadata or {}
        )
        entry.estimate_tokens()
        
        self.entries.append(entry)
        self.total_tokens += entry.token_count
        
        # Aplica limites
        self._apply_limits()
    
    def _apply_limits(self):
        """Aplica limites de memória (entries e tokens)"""
        # Remove entradas antigas se exceder limite
        while len(self.entries) > self.max_entries:
            removed = self.entries.pop(0)
            self.total_tokens -= removed.token_count
        
        # Remove entradas se exceder limite de tokens
        while self.total_tokens > self.max_tokens and len(self.entries) > 1:
            removed = self.entries.pop(0)
            self.total_tokens -= removed.token_count
    
    def get_recent_entries(self, n: int = 10) -> List[MemoryEntry]:
        """Retorna as N entradas mais recentes"""
        return self.entries[-n:]
    
    def get_entries_by_role(self, role: str) -> List[MemoryEntry]:
        """Retorna entradas de um role específico"""
        return [entry for entry in self.entries if entry.role == role]
    
    def get_entries_by_intent(self, intent: str) -> List[MemoryEntry]:
        """Retorna entradas com uma intenção específica"""
        return [entry for entry in self.entries if entry.intent == intent]
    
    def search_entries(self, keyword: str) -> List[MemoryEntry]:
        """Busca entradas que contêm palavra-chave"""
        keyword_lower = keyword.lower()
        return [entry for entry in self.entries 
                if keyword_lower in entry.content.lower()]
    
    def get_context_window(self, max_tokens: int = 2000) -> List[MemoryEntry]:
        """
        Retorna janela de contexto respeitando limite de tokens
        
        Args:
            max_tokens: Número máximo de tokens para contexto
            
        Returns:
            List[MemoryEntry]: Entradas mais recentes que cabem no limite
        """
        context = []
        tokens = 0
        
        # Itera de trás para frente (mais recente primeiro)
        for entry in reversed(self.entries):
            if tokens + entry.token_count <= max_tokens:
                context.insert(0, entry)
                tokens += entry.token_count
            else:
                break
        
        return context
    
    def create_summary(self, entries_to_summarize: Optional[int] = None) -> str:
        """
        Cria resumo das entradas antigas (placeholder para futura implementação)
        
        Args:
            entries_to_summarize: Número de entradas antigas para resumir
            
        Returns:
            str: Resumo criado
        """
        if entries_to_summarize is None:
            entries_to_summarize = len(self.entries) // 2
        
        # Por enquanto, apenas concatena as primeiras mensagens
        # TODO: Implementar resumo real usando LLM
        summary_entries = self.entries[:entries_to_summarize]
        
        summary_parts = []
        for entry in summary_entries:
            if entry.intent:
                summary_parts.append(f"{entry.role} ({entry.intent}): {entry.content[:50]}...")
            else:
                summary_parts.append(f"{entry.role}: {entry.content[:50]}...")
        
        self.summary = "Resumo da conversa anterior:\n" + "\n".join(summary_parts)
        
        # Remove entradas resumidas
        self.entries = self.entries[entries_to_summarize:]
        self.total_tokens = sum(e.token_count for e in self.entries)
        
        return self.summary
    
    def clear(self):
        """Limpa toda a memória"""
        self.entries.clear()
        self.summary = None
        self.total_tokens = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte memória para dicionário"""
        return {
            'entries': [entry.to_dict() for entry in self.entries],
            'summary': self.summary,
            'total_tokens': self.total_tokens,
            'max_entries': self.max_entries,
            'max_tokens': self.max_tokens
        }
    
    def to_messages_format(self) -> List[Dict[str, str]]:
        """Converte para formato de mensagens para LLM"""
        messages = []
        
        # Adiciona resumo se existir
        if self.summary:
            messages.append({
                'role': 'system',
                'content': self.summary
            })
        
        # Adiciona entradas
        for entry in self.entries:
            messages.append({
                'role': entry.role,
                'content': entry.content
            })
        
        return messages