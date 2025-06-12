"""
Pattern management for multilingual support.

This module handles language-specific patterns for intent detection
and content analysis without hardcoded strings.
"""

from typing import Dict, List, Set
from .constants import SupportedLanguages, InteractionPatterns


class PatternManager:
    """Manages language-specific patterns for content analysis."""
    
    def __init__(self):
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Load language-specific patterns."""
        return {
            SupportedLanguages.PORTUGUESE.value: {
                InteractionPatterns.GREETING_PATTERN.value: [
                    r'^(?:oi|olá|ola|hey|ei|bom dia|boa tarde|boa noite)',
                    r'^(?:tudo bem|como vai|beleza)',
                    r'^(?:e aí|e ai|qual boa)'
                ],
                InteractionPatterns.FAREWELL_PATTERN.value: [
                    r'(?:tchau|adeus|até|obrigad[oa]|valeu|flw)',
                    r'(?:bye|até logo|até mais|até breve)'
                ],
                InteractionPatterns.HELP_PATTERN.value: [
                    r'(?:ajuda|socorro|não entendi|como funciona)',
                    r'(?:o que você faz|que tipo de|para que serve)',
                    r'(?:preciso de ajuda|me ajude|pode ajudar)'
                ],
                InteractionPatterns.QUESTION_PATTERN.value: [
                    r'(?:questão|pergunta|exercício|problema)',
                    r'(?:quero|preciso|me dê|mostre)',
                    r'(?:matemática|português|física|química|biologia|história|geografia)'
                ],
                InteractionPatterns.EXPLANATION_PATTERN.value: [
                    r'(?:explique|o que é|como funciona|defina)',
                    r'(?:conceito|definição|significado)',
                    r'(?:ensine|demonstre|mostre como)'
                ],
                InteractionPatterns.AFFIRMATIVE_PATTERN.value: [
                    r'(?:sim|correto|certo|exato|isso mesmo)',
                    r'(?:ok|legal|beleza|perfeito)'
                ],
                InteractionPatterns.NEGATIVE_PATTERN.value: [
                    r'(?:não|errado|incorreto|negativo)',
                    r'(?:nunca|jamais|de jeito nenhum)'
                ],
                InteractionPatterns.TECHNICAL_TERMS.value: [
                    r'(?:matemática|física|química|biologia)',
                    r'(?:história|geografia|português|literatura)',
                    r'(?:álgebra|geometria|cálculo|equação)',
                    r'(?:conceito|teoria|definição|propriedade)'
                ]
            },
            
            SupportedLanguages.ENGLISH.value: {
                InteractionPatterns.GREETING_PATTERN.value: [
                    r'^(?:hi|hello|hey|good morning|good afternoon|good evening)',
                    r'^(?:how are you|what\'s up|how\'s it going)',
                    r'^(?:greetings|salutations)'
                ],
                InteractionPatterns.FAREWELL_PATTERN.value: [
                    r'(?:bye|goodbye|farewell|see you|thanks)',
                    r'(?:later|until|so long|take care)'
                ],
                InteractionPatterns.HELP_PATTERN.value: [
                    r'(?:help|assist|support|guide)',
                    r'(?:what do you do|what can you|how can you)',
                    r'(?:need help|can you help|please help)'
                ],
                InteractionPatterns.QUESTION_PATTERN.value: [
                    r'(?:question|problem|exercise|quiz)',
                    r'(?:want|need|give me|show me)',
                    r'(?:math|portuguese|physics|chemistry|biology|history|geography)'
                ],
                InteractionPatterns.EXPLANATION_PATTERN.value: [
                    r'(?:explain|what is|how does|define)',
                    r'(?:concept|definition|meaning)',
                    r'(?:teach|demonstrate|show how)'
                ],
                InteractionPatterns.AFFIRMATIVE_PATTERN.value: [
                    r'(?:yes|correct|right|exactly|that\'s right)',
                    r'(?:ok|good|perfect|great)'
                ],
                InteractionPatterns.NEGATIVE_PATTERN.value: [
                    r'(?:no|wrong|incorrect|negative)',
                    r'(?:never|not at all|absolutely not)'
                ],
                InteractionPatterns.TECHNICAL_TERMS.value: [
                    r'(?:mathematics|physics|chemistry|biology)',
                    r'(?:history|geography|portuguese|literature)',
                    r'(?:algebra|geometry|calculus|equation)',
                    r'(?:concept|theory|definition|property)'
                ]
            },
            
            SupportedLanguages.SPANISH.value: {
                InteractionPatterns.GREETING_PATTERN.value: [
                    r'^(?:hola|buenos días|buenas tardes|buenas noches)',
                    r'^(?:qué tal|cómo estás|cómo va)',
                    r'^(?:saludos|hola qué tal)'
                ],
                InteractionPatterns.FAREWELL_PATTERN.value: [
                    r'(?:adiós|hasta luego|nos vemos|gracias)',
                    r'(?:chao|hasta pronto|que tengas)'
                ],
                InteractionPatterns.HELP_PATTERN.value: [
                    r'(?:ayuda|asistencia|apoyo|guía)',
                    r'(?:qué haces|qué puedes|cómo puedes)',
                    r'(?:necesito ayuda|puedes ayudar|por favor ayuda)'
                ],
                InteractionPatterns.QUESTION_PATTERN.value: [
                    r'(?:pregunta|problema|ejercicio|quiz)',
                    r'(?:quiero|necesito|dame|muéstrame)',
                    r'(?:matemáticas|portugués|física|química|biología|historia|geografía)'
                ],
                InteractionPatterns.EXPLANATION_PATTERN.value: [
                    r'(?:explica|qué es|cómo funciona|define)',
                    r'(?:concepto|definición|significado)',
                    r'(?:enseña|demuestra|muestra cómo)'
                ],
                InteractionPatterns.AFFIRMATIVE_PATTERN.value: [
                    r'(?:sí|correcto|cierto|exacto|así es)',
                    r'(?:ok|bien|perfecto|genial)'
                ],
                InteractionPatterns.NEGATIVE_PATTERN.value: [
                    r'(?:no|incorrecto|negativo)',
                    r'(?:nunca|jamás|de ninguna manera)'
                ],
                InteractionPatterns.TECHNICAL_TERMS.value: [
                    r'(?:matemáticas|física|química|biología)',
                    r'(?:historia|geografía|portugués|literatura)',
                    r'(?:álgebra|geometría|cálculo|ecuación)',
                    r'(?:concepto|teoría|definición|propiedad)'
                ]
            },
            
            SupportedLanguages.FRENCH.value: {
                InteractionPatterns.GREETING_PATTERN.value: [
                    r'^(?:salut|bonjour|bonsoir|hello)',
                    r'^(?:comment allez-vous|comment ça va|ça va)',
                    r'^(?:coucou|hey)'
                ],
                InteractionPatterns.FAREWELL_PATTERN.value: [
                    r'(?:au revoir|à bientôt|salut|merci)',
                    r'(?:bye|à plus|à tout à l\'heure)'
                ],
                InteractionPatterns.HELP_PATTERN.value: [
                    r'(?:aide|assistance|support|guide)',
                    r'(?:que faites-vous|que pouvez-vous|comment pouvez)',
                    r'(?:besoin d\'aide|pouvez-vous aider|s\'il vous plaît aide)'
                ],
                InteractionPatterns.QUESTION_PATTERN.value: [
                    r'(?:question|problème|exercice|quiz)',
                    r'(?:veux|besoin|donnez-moi|montrez-moi)',
                    r'(?:mathématiques|portugais|physique|chimie|biologie|histoire|géographie)'
                ],
                InteractionPatterns.EXPLANATION_PATTERN.value: [
                    r'(?:expliquez|qu\'est-ce que|comment fonctionne|définir)',
                    r'(?:concept|définition|signification)',
                    r'(?:enseigner|démontrer|montrer comment)'
                ],
                InteractionPatterns.AFFIRMATIVE_PATTERN.value: [
                    r'(?:oui|correct|juste|exactement|c\'est ça)',
                    r'(?:ok|bien|parfait|génial)'
                ],
                InteractionPatterns.NEGATIVE_PATTERN.value: [
                    r'(?:non|faux|incorrect|négatif)',
                    r'(?:jamais|pas du tout|absolument pas)'
                ],
                InteractionPatterns.TECHNICAL_TERMS.value: [
                    r'(?:mathématiques|physique|chimie|biologie)',
                    r'(?:histoire|géographie|portugais|littérature)',
                    r'(?:algèbre|géométrie|calcul|équation)',
                    r'(?:concept|théorie|définition|propriété)'
                ]
            }
        }
    
    def get_patterns(self, language: str, pattern_type: str) -> List[str]:
        """Get patterns for a specific language and type."""
        return self.patterns.get(language, {}).get(pattern_type, [])
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the input text based on patterns."""
        text_lower = text.lower().strip()
        language_scores = {}
        
        for language, patterns in self.patterns.items():
            score = 0
            total_patterns = 0
            
            for pattern_type, pattern_list in patterns.items():
                total_patterns += len(pattern_list)
                for pattern in pattern_list:
                    if self._matches_pattern(text_lower, pattern):
                        score += 1
            
            if total_patterns > 0:
                language_scores[language] = score / total_patterns
        
        # Return language with highest score, default to Portuguese
        if language_scores:
            return max(language_scores, key=language_scores.get)
        return SupportedLanguages.PORTUGUESE.value
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches a pattern."""
        import re
        try:
            return bool(re.search(pattern, text))
        except re.error:
            return False
    
    def check_pattern_match(self, text: str, language: str, pattern_type: str) -> bool:
        """Check if text matches any pattern of the given type in the language."""
        patterns = self.get_patterns(language, pattern_type)
        text_lower = text.lower().strip()
        
        for pattern in patterns:
            if self._matches_pattern(text_lower, pattern):
                return True
        return False
    
    def contains_technical_terms(self, text: str, language: str = None) -> bool:
        """Check if text contains technical terms."""
        if language is None:
            language = self.detect_language(text)
        
        return self.check_pattern_match(text, language, InteractionPatterns.TECHNICAL_TERMS.value)