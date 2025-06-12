"""
Exemplos de treinamento para detecção de intenção multilíngue
"""

from typing import List
from .intent_models import IntentExample, IntentType, IntentEntity


# Exemplos para cada tipo de intenção em múltiplos idiomas
INTENT_EXAMPLES = [
    # REQUEST_QUESTION - Português
    IntentExample("Quero uma questão de matemática", IntentType.REQUEST_QUESTION, "pt", [
        IntentEntity("subject_area", "matemática")
    ]),
    IntentExample("Me dê uma questão fácil de português do ENEM", IntentType.REQUEST_QUESTION, "pt", [
        IntentEntity("subject_area", "português"),
        IntentEntity("difficulty", "fácil"),
        IntentEntity("exam", "ENEM")
    ]),
    IntentExample("Pode me dar um exercício de geografia?", IntentType.REQUEST_QUESTION, "pt", [
        IntentEntity("subject_area", "geografia")
    ]),
    IntentExample("Preciso de uma questão difícil de física", IntentType.REQUEST_QUESTION, "pt", [
        IntentEntity("subject_area", "física"),
        IntentEntity("difficulty", "difícil")
    ]),
    IntentExample("Mostre uma pergunta sobre história do Brasil", IntentType.REQUEST_QUESTION, "pt", [
        IntentEntity("subject_area", "história"),
        IntentEntity("topic", "Brasil")
    ]),
    
    # REQUEST_QUESTION - English
    IntentExample("I want a math question", IntentType.REQUEST_QUESTION, "en", [
        IntentEntity("subject_area", "math")
    ]),
    IntentExample("Give me an easy Portuguese question from ENEM", IntentType.REQUEST_QUESTION, "en", [
        IntentEntity("subject_area", "portuguese"),
        IntentEntity("difficulty", "easy"),
        IntentEntity("exam", "ENEM")
    ]),
    IntentExample("Can you show me a geography exercise?", IntentType.REQUEST_QUESTION, "en", [
        IntentEntity("subject_area", "geography")
    ]),
    
    # REQUEST_QUESTION - Spanish
    IntentExample("Quiero una pregunta de matemáticas", IntentType.REQUEST_QUESTION, "es", [
        IntentEntity("subject_area", "matemáticas")
    ]),
    IntentExample("Dame una pregunta fácil de portugués del ENEM", IntentType.REQUEST_QUESTION, "es", [
        IntentEntity("subject_area", "portugués"),
        IntentEntity("difficulty", "fácil"),
        IntentEntity("exam", "ENEM")
    ]),
    
    # ANSWER_QUESTION - Português
    IntentExample("A resposta é alternativa A", IntentType.ANSWER_QUESTION, "pt", [
        IntentEntity("answer", "A")
    ]),
    IntentExample("Letra B", IntentType.ANSWER_QUESTION, "pt", [
        IntentEntity("answer", "B")
    ]),
    IntentExample("Acho que é a C", IntentType.ANSWER_QUESTION, "pt", [
        IntentEntity("answer", "C")
    ]),
    IntentExample("alternativa D, por favor", IntentType.ANSWER_QUESTION, "pt", [
        IntentEntity("answer", "D")
    ]),
    IntentExample("É a opção E", IntentType.ANSWER_QUESTION, "pt", [
        IntentEntity("answer", "E")
    ]),
    
    # ANSWER_QUESTION - English
    IntentExample("The answer is alternative A", IntentType.ANSWER_QUESTION, "en", [
        IntentEntity("answer", "A")
    ]),
    IntentExample("Letter B", IntentType.ANSWER_QUESTION, "en", [
        IntentEntity("answer", "B")
    ]),
    IntentExample("I think it's C", IntentType.ANSWER_QUESTION, "en", [
        IntentEntity("answer", "C")
    ]),
    
    # REQUEST_EXPLANATION - Português
    IntentExample("Por que está errado?", IntentType.REQUEST_EXPLANATION, "pt"),
    IntentExample("Pode explicar melhor?", IntentType.REQUEST_EXPLANATION, "pt"),
    IntentExample("Não entendi, pode detalhar?", IntentType.REQUEST_EXPLANATION, "pt"),
    IntentExample("Me explique por que a resposta é essa", IntentType.REQUEST_EXPLANATION, "pt"),
    
    # REQUEST_EXPLANATION - English
    IntentExample("Why is it wrong?", IntentType.REQUEST_EXPLANATION, "en"),
    IntentExample("Can you explain better?", IntentType.REQUEST_EXPLANATION, "en"),
    IntentExample("I don't understand, can you detail?", IntentType.REQUEST_EXPLANATION, "en"),
    
    # REQUEST_REFERENCE - Português
    IntentExample("Tem material de estudo sobre isso?", IntentType.REQUEST_REFERENCE, "pt"),
    IntentExample("Onde posso estudar mais sobre esse tema?", IntentType.REQUEST_REFERENCE, "pt"),
    IntentExample("Me indica links para estudar", IntentType.REQUEST_REFERENCE, "pt"),
    IntentExample("Quais são as referências dessa questão?", IntentType.REQUEST_REFERENCE, "pt"),
    
    # REQUEST_REFERENCE - English
    IntentExample("Do you have study material about this?", IntentType.REQUEST_REFERENCE, "en"),
    IntentExample("Where can I study more about this topic?", IntentType.REQUEST_REFERENCE, "en"),
    
    # GENERAL_CHAT - Português
    IntentExample("O que você acha sobre educação no Brasil?", IntentType.GENERAL_CHAT, "pt"),
    IntentExample("Como funciona o ENEM?", IntentType.GENERAL_CHAT, "pt"),
    IntentExample("Qual a importância de estudar matemática?", IntentType.GENERAL_CHAT, "pt"),
    
    # GENERAL_CHAT - English
    IntentExample("What do you think about education in Brazil?", IntentType.GENERAL_CHAT, "en"),
    IntentExample("How does ENEM work?", IntentType.GENERAL_CHAT, "en"),
    
    # GREETING - Multilingual
    IntentExample("Olá", IntentType.GREETING, "pt"),
    IntentExample("Oi", IntentType.GREETING, "pt"),
    IntentExample("Bom dia", IntentType.GREETING, "pt"),
    IntentExample("Boa tarde", IntentType.GREETING, "pt"),
    IntentExample("Boa noite", IntentType.GREETING, "pt"),
    IntentExample("Hello", IntentType.GREETING, "en"),
    IntentExample("Hi", IntentType.GREETING, "en"),
    IntentExample("Good morning", IntentType.GREETING, "en"),
    IntentExample("Hola", IntentType.GREETING, "es"),
    IntentExample("Buenos días", IntentType.GREETING, "es"),
    
    # FAREWELL - Multilingual
    IntentExample("Tchau", IntentType.FAREWELL, "pt"),
    IntentExample("Até mais", IntentType.FAREWELL, "pt"),
    IntentExample("Obrigado e tchau", IntentType.FAREWELL, "pt"),
    IntentExample("Bye", IntentType.FAREWELL, "en"),
    IntentExample("Goodbye", IntentType.FAREWELL, "en"),
    IntentExample("See you later", IntentType.FAREWELL, "en"),
    IntentExample("Adiós", IntentType.FAREWELL, "es"),
    
    # REQUEST_STUDY_PLAN - Português
    IntentExample("Quero um plano de estudos", IntentType.REQUEST_STUDY_PLAN, "pt"),
    IntentExample("Como devo estudar para o ENEM?", IntentType.REQUEST_STUDY_PLAN, "pt"),
    IntentExample("Me ajuda a montar um cronograma de estudos", IntentType.REQUEST_STUDY_PLAN, "pt"),
    
    # REQUEST_PROGRESS - Português
    IntentExample("Como está meu desempenho?", IntentType.REQUEST_PROGRESS, "pt"),
    IntentExample("Quero ver meu progresso", IntentType.REQUEST_PROGRESS, "pt"),
    IntentExample("Quantas questões eu acertei?", IntentType.REQUEST_PROGRESS, "pt"),
    
    # REQUEST_STATISTICS - Português
    IntentExample("Me mostre minhas estatísticas", IntentType.REQUEST_STATISTICS, "pt"),
    IntentExample("Qual minha taxa de acerto em matemática?", IntentType.REQUEST_STATISTICS, "pt"),
    IntentExample("Quero ver meus resultados", IntentType.REQUEST_STATISTICS, "pt"),
    
    # HELP - Multilingual
    IntentExample("Ajuda", IntentType.HELP, "pt"),
    IntentExample("Como funciona?", IntentType.HELP, "pt"),
    IntentExample("O que você pode fazer?", IntentType.HELP, "pt"),
    IntentExample("Help", IntentType.HELP, "en"),
    IntentExample("How does it work?", IntentType.HELP, "en"),
    IntentExample("What can you do?", IntentType.HELP, "en"),
    
    # FEEDBACK - Português
    IntentExample("Quero dar um feedback", IntentType.FEEDBACK, "pt"),
    IntentExample("Tenho uma sugestão", IntentType.FEEDBACK, "pt"),
    IntentExample("Encontrei um erro no sistema", IntentType.FEEDBACK, "pt"),
]


def get_examples_by_intent(intent_type: IntentType) -> List[IntentExample]:
    """Retorna todos os exemplos de um tipo de intenção específico"""
    return [ex for ex in INTENT_EXAMPLES if ex.intent_type == intent_type]


def get_examples_by_language(language: str) -> List[IntentExample]:
    """Retorna todos os exemplos de um idioma específico"""
    return [ex for ex in INTENT_EXAMPLES if ex.language == language]


def get_all_examples() -> List[IntentExample]:
    """Retorna todos os exemplos de treinamento"""
    return INTENT_EXAMPLES