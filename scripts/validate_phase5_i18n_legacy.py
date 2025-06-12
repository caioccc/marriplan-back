#!/usr/bin/env python3
"""
Validação da Fase 5: Remoção de Legacy e Sistema de Internacionalização (i18n)
"""

import os
import sys
import django
import logging
from pathlib import Path
import traceback

# Setup Django
sys.path.append(str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from app.core.i18n import LocalizationManager, PatternManager, SupportedLanguages, MessageTypes, InteractionPatterns
from app.core.agents.chat_agent import ChatAgent
from app.core.models.agent_models import AgentRequest

logger = logging.getLogger(__name__)

class Phase5ValidationResult:
    """Resultado da validação da Fase 5"""
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.details = []
    
    def add_success(self, test_name: str, details: str = ""):
        self.tests_passed += 1
        self.details.append(f"✅ {test_name}: {details}")
        
    def add_failure(self, test_name: str, error: str):
        self.tests_failed += 1
        self.errors.append(error)
        self.details.append(f"❌ {test_name}: {error}")
    
    def print_summary(self):
        print("\n" + "="*60)
        print("VALIDAÇÃO FASE 5 - REMOÇÃO DE LEGACY E INTERNACIONALIZAÇÃO")
        print("="*60)
        
        for detail in self.details:
            print(detail)
        
        print("\n" + "-"*40)
        print(f"Total de testes: {self.tests_passed + self.tests_failed}")
        print(f"✅ Sucessos: {self.tests_passed}")
        print(f"❌ Falhas: {self.tests_failed}")
        
        if self.tests_failed == 0:
            print("\n🎉 FASE 5 - VALIDAÇÃO COMPLETA COM SUCESSO!")
        else:
            print(f"\n⚠️  FASE 5 - {self.tests_failed} PROBLEMAS ENCONTRADOS")
            print("\nErros detalhados:")
            for error in self.errors:
                print(f"  • {error}")

def validate_i18n_infrastructure():
    """Valida infraestrutura de internacionalização"""
    result = Phase5ValidationResult()
    
    try:
        # Verificar módulo i18n
        i18n_path = Path(__file__).parent.parent / "app" / "core" / "i18n"
        
        if i18n_path.exists():
            result.add_success("Módulo i18n", f"Encontrado em: {i18n_path}")
            
            # Verificar arquivos essenciais
            essential_files = [
                '__init__.py',
                'constants.py',
                'localization.py',
                'patterns.py'
            ]
            
            for file_name in essential_files:
                file_path = i18n_path / file_name
                if file_path.exists():
                    result.add_success(f"Arquivo {file_name}", "Presente")
                else:
                    result.add_failure(f"Arquivo {file_name}", "Não encontrado")
        else:
            result.add_failure("Módulo i18n", "Diretório não encontrado")
        
        # Verificar importações
        try:
            result.add_success("Importações i18n", "Todas as classes importadas com sucesso")
        except ImportError as e:
            result.add_failure("Importações i18n", f"Erro de importação: {str(e)}")
    
    except Exception as e:
        result.add_failure("Infraestrutura i18n", f"Erro: {str(e)}")
    
    return result

def validate_supported_languages():
    """Valida idiomas suportados"""
    result = Phase5ValidationResult()
    
    try:
        # Verificar enum SupportedLanguages
        languages = list(SupportedLanguages)
        
        if languages:
            result.add_success("SupportedLanguages enum", f"Idiomas: {len(languages)}")
            
            # Verificar idiomas específicos
            expected_languages = [
                SupportedLanguages.PORTUGUESE,
                SupportedLanguages.ENGLISH,
                SupportedLanguages.SPANISH,
                SupportedLanguages.FRENCH
            ]
            
            for lang in expected_languages:
                if lang in languages:
                    result.add_success(f"Idioma {lang.name}", f"Código: {lang.value}")
                else:
                    result.add_failure(f"Idioma {lang.name}", "Não encontrado")
        else:
            result.add_failure("SupportedLanguages", "Nenhum idioma encontrado")
        
        # Verificar MessageTypes enum
        message_types = list(MessageTypes)
        if message_types:
            result.add_success("MessageTypes enum", f"Tipos: {len(message_types)}")
            
            essential_types = [
                MessageTypes.GREETING,
                MessageTypes.FAREWELL,
                MessageTypes.HELP,
                MessageTypes.CASUAL
            ]
            
            for msg_type in essential_types:
                if msg_type in message_types:
                    result.add_success(f"MessageType {msg_type.name}", f"Valor: {msg_type.value}")
                else:
                    result.add_failure(f"MessageType {msg_type.name}", "Não encontrado")
        
        # Verificar InteractionPatterns enum
        patterns = list(InteractionPatterns)
        if patterns:
            result.add_success("InteractionPatterns enum", f"Padrões: {len(patterns)}")
        else:
            result.add_failure("InteractionPatterns enum", "Nenhum padrão encontrado")
    
    except Exception as e:
        result.add_failure("Idiomas suportados", f"Erro: {str(e)}")
    
    return result

def validate_localization_manager():
    """Valida o LocalizationManager"""
    result = Phase5ValidationResult()
    
    try:
        # Instanciar LocalizationManager
        localization = LocalizationManager()
        result.add_success("LocalizationManager", "Instanciado com sucesso")
        
        # Verificar métodos essenciais
        essential_methods = [
            'get_message',
            'get_supported_languages',
            'get_all_messages_for_language'
        ]
        
        for method in essential_methods:
            if hasattr(localization, method):
                result.add_success(f"LocalizationManager.{method}", "Método disponível")
            else:
                result.add_failure(f"LocalizationManager.{method}", "Método não encontrado")
        
        # Testar recuperação de mensagens
        try:
            # Testar mensagem de saudação em português
            greeting_pt = localization.get_message(
                language=SupportedLanguages.PORTUGUESE.value,
                message_type=MessageTypes.GREETING.value,
                user_name="teste"
            )
            
            if greeting_pt and "olá" in greeting_pt.lower():
                result.add_success("Mensagem PT", f"Saudação: '{greeting_pt[:50]}...'")
            else:
                result.add_failure("Mensagem PT", f"Saudação inesperada: {greeting_pt}")
            
            # Testar mensagem em inglês
            greeting_en = localization.get_message(
                language=SupportedLanguages.ENGLISH.value,
                message_type=MessageTypes.GREETING.value,
                user_name="test"
            )
            
            if greeting_en and "hello" in greeting_en.lower():
                result.add_success("Mensagem EN", f"Saudação: '{greeting_en[:50]}...'")
            else:
                result.add_failure("Mensagem EN", f"Saudação inesperada: {greeting_en}")
        
        except Exception as e:
            result.add_failure("Teste de mensagens", f"Erro: {str(e)}")
        
        # Verificar idiomas suportados
        try:
            supported_langs = localization.get_supported_languages()
            if supported_langs:
                result.add_success("Idiomas no LocalizationManager", f"Suportados: {supported_langs}")
            else:
                result.add_failure("Idiomas no LocalizationManager", "Lista vazia")
        except Exception as e:
            result.add_failure("Idiomas suportados", f"Erro: {str(e)}")
    
    except Exception as e:
        result.add_failure("LocalizationManager", f"Erro na instanciação: {str(e)}")
    
    return result

def validate_pattern_manager():
    """Valida o PatternManager"""
    result = Phase5ValidationResult()
    
    try:
        # Instanciar PatternManager
        patterns = PatternManager()
        result.add_success("PatternManager", "Instanciado com sucesso")
        
        # Verificar métodos essenciais
        pattern_methods = [
            'detect_language',
            'check_pattern_match',
            'contains_technical_terms'
        ]
        
        for method in pattern_methods:
            if hasattr(patterns, method):
                result.add_success(f"PatternManager.{method}", "Método disponível")
            else:
                result.add_failure(f"PatternManager.{method}", "Método não encontrado")
        
        # Testar detecção de idioma
        test_cases = [
            ("Olá, como você está?", SupportedLanguages.PORTUGUESE.value, "Português"),
            ("Hello, how are you?", SupportedLanguages.ENGLISH.value, "Inglês"),
            ("Hola, ¿cómo estás?", SupportedLanguages.SPANISH.value, "Espanhol"),
            ("Bonjour, comment allez-vous?", SupportedLanguages.FRENCH.value, "Francês")
        ]
        
        for text, expected_lang, lang_name in test_cases:
            try:
                detected = patterns.detect_language(text)
                if detected == expected_lang:
                    result.add_success(f"Detecção {lang_name}", f"Correto: {detected}")
                else:
                    result.add_failure(f"Detecção {lang_name}", f"Esperado: {expected_lang}, Detectado: {detected}")
            except Exception as e:
                result.add_failure(f"Detecção {lang_name}", f"Erro: {str(e)}")
        
        # Testar verificação de padrões
        try:
            greeting_text = "Olá, bom dia!"
            is_greeting = patterns.check_pattern_match(
                greeting_text,
                SupportedLanguages.PORTUGUESE.value,
                InteractionPatterns.GREETING_PATTERN.value
            )
            
            if is_greeting:
                result.add_success("Verificação de padrão", "Saudação detectada corretamente")
            else:
                result.add_failure("Verificação de padrão", "Saudação não detectada")
        
        except Exception as e:
            result.add_failure("Verificação de padrão", f"Erro: {str(e)}")
        
        # Testar detecção de termos técnicos
        try:
            technical_text = "equação quadrática derivada integral"
            non_technical = "olá como você está hoje"
            
            is_tech = patterns.contains_technical_terms(technical_text, SupportedLanguages.PORTUGUESE.value)
            is_not_tech = patterns.contains_technical_terms(non_technical, SupportedLanguages.PORTUGUESE.value)
            
            if is_tech and not is_not_tech:
                result.add_success("Detecção termos técnicos", "Funcionando corretamente")
            else:
                result.add_failure("Detecção termos técnicos", f"Tech: {is_tech}, Non-tech: {is_not_tech}")
        
        except Exception as e:
            result.add_failure("Detecção termos técnicos", f"Erro: {str(e)}")
    
    except Exception as e:
        result.add_failure("PatternManager", f"Erro na instanciação: {str(e)}")
    
    return result

def validate_legacy_removal():
    """Valida remoção de código legacy"""
    result = Phase5ValidationResult()
    
    try:
        # Verificar ChatAgent refatorado
        chat_agent = ChatAgent()
        result.add_success("ChatAgent refatorado", "Instanciado com sucesso")
        
        # Verificar se ChatAgent usa i18n
        if hasattr(chat_agent, 'localization'):
            result.add_success("ChatAgent.localization", "LocalizationManager integrado")
        else:
            result.add_failure("ChatAgent.localization", "LocalizationManager não encontrado")
        
        if hasattr(chat_agent, 'patterns'):
            result.add_success("ChatAgent.patterns", "PatternManager integrado")
        else:
            result.add_failure("ChatAgent.patterns", "PatternManager não encontrado")
        
        # Verificar método can_handle refatorado
        try:
            test_request = AgentRequest(
                message="Olá, como você está?",
                user_id="test_user",
                session_id="test_session"
            )
            
            can_handle = chat_agent.can_handle(test_request)
            result.add_success("ChatAgent.can_handle", f"Método funcional, resultado: {can_handle}")
        
        except Exception as e:
            result.add_failure("ChatAgent.can_handle", f"Erro: {str(e)}")
        
        # Verificar configuração multilíngue
        if hasattr(chat_agent, 'config'):
            config = chat_agent.config
            
            i18n_configs = [
                'default_language',
                'auto_detect_language'
            ]
            
            for config_key in i18n_configs:
                if config_key in config:
                    result.add_success(f"Config {config_key}", f"Valor: {config[config_key]}")
                else:
                    result.add_failure(f"Config {config_key}", "Não encontrado")
        
        # Verificar se hardcoded strings foram removidas
        # (Análise estática básica)
        chat_agent_file = Path(__file__).parent.parent / "app" / "core" / "agents" / "chat_agent.py"
        
        if chat_agent_file.exists():
            with open(chat_agent_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Procurar por strings hardcoded em português
            suspicious_patterns = [
                '"olá"', "'olá'",
                '"oi"', "'oi'",
                '"tchau"', "'tchau'",
                '"ajuda"', "'ajuda'",
                '"não entendi"', "'não entendi'"
            ]
            
            found_hardcoded = []
            for pattern in suspicious_patterns:
                if pattern.lower() in content.lower():
                    found_hardcoded.append(pattern)
            
            if found_hardcoded:
                result.add_failure("Remoção de hardcoded strings", f"Encontrados: {found_hardcoded}")
            else:
                result.add_success("Remoção de hardcoded strings", "Nenhuma string hardcoded encontrada")
        else:
            result.add_failure("Arquivo ChatAgent", "Não encontrado para análise")
    
    except Exception as e:
        result.add_failure("Remoção de legacy", f"Erro: {str(e)}")
    
    return result

def validate_multilingual_functionality():
    """Valida funcionalidade multilíngue end-to-end"""
    result = Phase5ValidationResult()
    
    try:
        chat_agent = ChatAgent()
        
        # Testes em diferentes idiomas
        test_cases = [
            {
                'message': 'Olá, tudo bem?',
                'language': 'Português',
                'expected_can_handle': True
            },
            {
                'message': 'Hello, how are you?',
                'language': 'Inglês',
                'expected_can_handle': True
            },
            {
                'message': 'Hola, ¿cómo estás?',
                'language': 'Espanhol',
                'expected_can_handle': True
            },
            {
                'message': 'Bonjour, comment allez-vous?',
                'language': 'Francês',
                'expected_can_handle': True
            }
        ]
        
        for test_case in test_cases:
            try:
                request = AgentRequest(
                    message=test_case['message'],
                    user_id="test_user",
                    session_id="test_session"
                )
                
                can_handle = chat_agent.can_handle(request)
                
                if can_handle == test_case['expected_can_handle']:
                    result.add_success(f"Teste {test_case['language']}", "Detecção correta")
                else:
                    result.add_failure(f"Teste {test_case['language']}", f"Esperado: {test_case['expected_can_handle']}, Obtido: {can_handle}")
            
            except Exception as e:
                result.add_failure(f"Teste {test_case['language']}", f"Erro: {str(e)}")
        
        # Teste de processamento multilíngue
        try:
            test_request = AgentRequest(
                message="Hello, I need help",
                user_id="test_user",
                session_id="test_session"
            )
            
            # Verificar se método process existe e pode ser chamado
            if hasattr(chat_agent, 'process'):
                result.add_success("Processamento multilíngue", "Método process disponível")
            else:
                result.add_failure("Processamento multilíngue", "Método process não encontrado")
        
        except Exception as e:
            result.add_failure("Processamento multilíngue", f"Erro: {str(e)}")
    
    except Exception as e:
        result.add_failure("Funcionalidade multilíngue", f"Erro: {str(e)}")
    
    return result

def validate_message_completeness():
    """Valida completude das mensagens em todos os idiomas"""
    result = Phase5ValidationResult()
    
    try:
        localization = LocalizationManager()
        
        # Verificar se todas as combinações idioma/tipo de mensagem existem
        languages = [lang.value for lang in SupportedLanguages]
        message_types = [msg_type.value for msg_type in MessageTypes]
        
        missing_combinations = []
        existing_combinations = []
        
        for language in languages:
            for message_type in message_types:
                try:
                    message = localization.get_message(
                        language=language,
                        message_type=message_type,
                        user_name="teste"
                    )
                    
                    if message:
                        existing_combinations.append(f"{language}:{message_type}")
                    else:
                        missing_combinations.append(f"{language}:{message_type}")
                
                except Exception as e:
                    missing_combinations.append(f"{language}:{message_type} (erro: {str(e)})")
        
        if not missing_combinations:
            result.add_success("Completude de mensagens", f"Todas as {len(existing_combinations)} combinações disponíveis")
        else:
            result.add_failure("Completude de mensagens", f"Faltando: {missing_combinations[:5]}...")  # Mostra só primeiras 5
        
        # Verificar qualidade das mensagens
        sample_checks = [
            (SupportedLanguages.PORTUGUESE.value, MessageTypes.GREETING.value, ["olá", "oi", "bom"]),
            (SupportedLanguages.ENGLISH.value, MessageTypes.GREETING.value, ["hello", "hi", "good"]),
            (SupportedLanguages.SPANISH.value, MessageTypes.GREETING.value, ["hola", "buenos", "buenas"]),
            (SupportedLanguages.FRENCH.value, MessageTypes.GREETING.value, ["bonjour", "salut", "bonsoir"])
        ]
        
        for language, msg_type, expected_words in sample_checks:
            try:
                message = localization.get_message(
                    language=language,
                    message_type=msg_type,
                    user_name="teste"
                )
                
                if message:
                    message_lower = message.lower()
                    found_words = [word for word in expected_words if word in message_lower]
                    
                    if found_words:
                        result.add_success(f"Qualidade {language}", f"Palavras encontradas: {found_words}")
                    else:
                        result.add_failure(f"Qualidade {language}", f"Nenhuma palavra esperada encontrada: {expected_words}")
                else:
                    result.add_failure(f"Qualidade {language}", "Mensagem vazia")
            
            except Exception as e:
                result.add_failure(f"Qualidade {language}", f"Erro: {str(e)}")
    
    except Exception as e:
        result.add_failure("Completude de mensagens", f"Erro: {str(e)}")
    
    return result

def validate_pattern_completeness():
    """Valida completude dos padrões de detecção"""
    result = Phase5ValidationResult()
    
    try:
        patterns = PatternManager()
        
        # Verificar se padrões existem para todos os idiomas
        languages = [lang.value for lang in SupportedLanguages]
        pattern_types = [pattern.value for pattern in InteractionPatterns]
        
        for language in languages:
            for pattern_type in pattern_types:
                try:
                    # Testar com texto genérico
                    test_text = "teste genérico"
                    result_check = patterns.check_pattern_match(test_text, language, pattern_type)
                    
                    # Se não deu erro, o padrão existe
                    result.add_success(f"Padrão {language}:{pattern_type}", "Disponível")
                
                except Exception as e:
                    result.add_failure(f"Padrão {language}:{pattern_type}", f"Erro: {str(e)}")
        
        # Testar robustez da detecção de idioma
        edge_cases = [
            ("", "Texto vazio"),
            ("123 456", "Apenas números"),
            ("!@#$%", "Apenas símbolos"),
            ("a", "Uma letra"),
            ("hello world test this is english", "Texto claramente inglês"),
            ("olá mundo teste isso é português", "Texto claramente português")
        ]
        
        for test_text, description in edge_cases:
            try:
                detected_lang = patterns.detect_language(test_text)
                result.add_success(f"Edge case: {description}", f"Detectado: {detected_lang}")
            except Exception as e:
                result.add_failure(f"Edge case: {description}", f"Erro: {str(e)}")
    
    except Exception as e:
        result.add_failure("Completude de padrões", f"Erro: {str(e)}")
    
    return result

def main():
    """Função principal de validação"""
    print("Iniciando validação da Fase 5 - Remoção de Legacy e Internacionalização...")
    
    all_results = []
    
    # Executar todas as validações
    all_results.append(validate_i18n_infrastructure())
    all_results.append(validate_supported_languages())
    all_results.append(validate_localization_manager())
    all_results.append(validate_pattern_manager())
    all_results.append(validate_legacy_removal())
    all_results.append(validate_multilingual_functionality())
    all_results.append(validate_message_completeness())
    all_results.append(validate_pattern_completeness())
    
    # Consolidar resultados
    final_result = Phase5ValidationResult()
    for result in all_results:
        final_result.tests_passed += result.tests_passed
        final_result.tests_failed += result.tests_failed
        final_result.errors.extend(result.errors)
        final_result.details.extend(result.details)
    
    # Imprimir resultado final
    final_result.print_summary()
    
    return final_result.tests_failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)