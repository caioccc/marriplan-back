"""
Localization manager for multilingual support.

This module provides localized messages and templates for different languages.
"""

from typing import Dict, List, Optional
import random
from datetime import datetime
from .constants import SupportedLanguages, MessageTypes


class LocalizationManager:
    """Manages localized messages and templates."""

    def __init__(self):
        self.messages = self._load_messages()

    def _load_messages(self) -> Dict[str, Dict[str, List[str]]]:
        """Load localized messages for all supported languages."""
        return {
            SupportedLanguages.PORTUGUESE.value: {
                MessageTypes.GREETING.value: [
                    # Estilo amigável
                    "{time_greeting}! 😊 Como posso ajudar você hoje?",
                    "Olá! 👋 Pronto para estudar hoje?",
                    "{time_greeting}! Estou aqui para ajudar com seus estudos. Em que posso ser útil?",
                    "Oi! 😄 Que bom ver você aqui! Como posso ajudar?",
                    "{time_greeting}, {user_name}! 🌟 Vamos estudar juntos hoje?",

                    # Estilo entusiasmado
                    "Eaí! 🔥 Pronto para arrasar nos estudos hoje?",
                    "Opa! 🚀 Chegou a hora de aprender coisas incríveis!",
                    "Olá! ⚡ Que energia boa! Vamos estudar com garra hoje?",
                    "E aí, jovem! 💪 Bora transformar conhecimento em poder?",
                    "Heyyy! 🎯 Preparado para uma sessão épica de estudos?",

                    # Estilo acolhedor
                    "Seja bem-vindo(a)! 🤗 Estou aqui para tornar seus estudos mais fáceis.",
                    "Que prazer ter você aqui! 💝 Como posso apoiar seu aprendizado hoje?",
                    "Oi, querido(a)! 🌸 Vamos aprender juntos de forma tranquila?",
                    "Olá! 🕊️ Estou aqui para ser seu companheiro de estudos. No que posso ajudar?",

                    # Estilo motivacional
                    "Olá, futuro(a) expert! 🏆 Pronto para mais um passo rumo ao sucesso?",
                    "E aí, campeão(ã)! 🥇 Vamos conquistar mais conhecimento hoje?",
                    "Oi! 💎 Cada pergunta sua é um investimento no seu futuro brilhante!",
                    "Saudações, estudante dedicado(a)! 🌟 Vamos brilhar juntos?"
                ],

                MessageTypes.FAREWELL.value: [
                    # Despedidas motivacionais
                    "Até logo! 👋 Continue estudando e boa sorte!",
                    "Tchau! 😊 Espero ter ajudado. Volte sempre!",
                    "Obrigado por usar o {system_name}! 🎓 Até a próxima!",
                    "Adeus! 🌟 Continue se dedicando aos estudos!",
                    "Até mais! 📚 Sucesso nos seus estudos!",

                    # Despedidas encorajadoras
                    "Vai com tudo! 🚀 Você está no caminho certo!",
                    "Até a próxima! 💪 Lembre-se: cada estudo conta!",
                    "Tchau! 🎯 Confio no seu potencial, continue assim!",
                    "Até logo! ⭐ Você está construindo um futuro incrível!",
                    "Adeus! 🔥 Mantenha essa dedicação que você vai longe!",

                    # Despedidas carinhosas
                    "Até breve! 💕 Foi um prazer estudar com você!",
                    "Tchau, querido(a)! 🌺 Cuide-se e estude com carinho!",
                    "Até logo! 🤗 Lembre-se: eu sempre estarei aqui para ajudar!",
                    "Adeus! 🌙 Que seus sonhos sejam repletos de conhecimento!"
                ],

                MessageTypes.HELP.value: [
                    # Ajuda detalhada
                    "Claro! 😊 Estou aqui para ajudar com seus estudos. Posso:\\n• Explicar conceitos\\n• Fornecer questões para praticar\\n• Buscar materiais de estudo\\n• Dar dicas de estudo\\n\\nO que você gostaria de fazer?",
                    "Com certeza! 🤝 Sou seu assistente de estudos. Posso ajudar com explicações, questões, referências e muito mais. Do que você precisa?",
                    "Estou aqui para isso! 📚 Posso explicar conceitos, criar questões, encontrar materiais... Conte-me o que você quer estudar!",
                    "Vamos lá! 🚀 Posso ajudar com várias coisas: tirar dúvidas, praticar com questões, encontrar referências... O que você tem em mente?",

                    # Ajuda interativa
                    "Perfeito! 🎯 Sou especialista em:\\n\\n📖 Explicações claras e didáticas\\n🧩 Questões personalizadas\\n🔍 Busca de materiais específicos\\n💡 Dicas de estudo eficazes\\n🎓 Preparação para provas\\n\\nQual dessas opções te interessa mais?",
                    "Adoraria ajudar! 💫 Posso ser seu:\\n\\n🤖 Tutor particular\\n📚 Biblioteca pessoal\\n🎯 Treinador de questões\\n💭 Consultor de estudos\\n\\nComo prefere que eu te apoie hoje?",
                    "Maravilha! 🌟 Tenho superpoderes em:\\n\\n⚡ Explicações que fazem 'clicar'\\n🎲 Questões desafiadoras\\n🔮 Materiais sob medida\\n🚀 Estratégias de estudo\\n\\nQual superpower você quer testar primeiro?",

                    # Ajuda encorajadora
                    "Que ótimo! 💪 Estou aqui para ser seu parceiro de estudos. Juntos, vamos transformar suas dúvidas em conhecimento sólido! Por onde começamos?",
                    "Claro que sim! 🌈 Todo grande aprendizado começa com uma pergunta. Estou pronto para te acompanhar nessa jornada. O que você quer descobrir?",
                    "Sempre! 🤗 Adoro ajudar estudantes dedicados como você. Vamos fazer deste momento uma experiência de aprendizado incrível! Qual seu desafio?"
                ],

                MessageTypes.ERROR.value: [
                    "Ops! 😅 Parece que algo deu errado. Pode tentar novamente?",
                    "Desculpe! 🤔 Tive um problema para processar isso. Vamos tentar de novo?",
                    "Eita! 😬 Houve um pequeno erro. Reformule sua pergunta, por favor?",
                    "Oops! 🙃 Algo não funcionou como esperado. Pode repetir de outra forma?"
                ],

                MessageTypes.SUCCESS.value: [
                    "Perfeito! ✅ Conseguimos!",
                    "Excelente! 🎉 Deu tudo certo!",
                    "Ótimo! 👍 Funcionou perfeitamente!",
                    "Sucesso! 🌟 Missão cumprida!"
                ],

                MessageTypes.ENCOURAGEMENT.value: [
                    "Você está indo muito bem! 🌟 Continue assim que o sucesso é inevitável!",
                    "Que progresso incrível! 💪 Estou orgulhoso da sua dedicação!",
                    "Excelente! 🏆 Cada passo seu é uma vitória que merece ser celebrada!",
                    "Parabéns! 🎉 Sua persistência é inspiradora!",
                    "Fantástico! ⚡ Você está provando que dedicação sempre vale a pena!",
                    "Maravilhoso! 🦋 Sua evolução é visível e emocionante!",
                    "Sensacional! 🎯 Você está construindo um futuro brilhante!"
                ],

                MessageTypes.STUDY_TIPS.value: [
                    "💡 Dica valiosa: Que tal fazer um resumo do que aprendeu hoje? Ajuda muito na fixação!",
                    "🎯 Estratégia inteligente: Intercale matérias diferentes - seu cérebro agradece!",
                    "⏰ Técnica comprovada: Estude por 25 minutos, descanse 5. É o método Pomodoro!",
                    "📚 Segredo de expert: Ensine para alguém o que aprendeu - é a melhor forma de fixar!",
                    "🧠 Hack mental: Conecte conceitos novos com coisas que você já sabe!",
                    "🌟 Pro tip: Comemore suas pequenas vitórias - elas motivam para as grandes!",
                    "🔄 Técnica ninja: Revise o conteúdo após 1 dia, 1 semana e 1 mês!"
                ],

                MessageTypes.ABOUT_SYSTEM.value: [
                    "Sou o assistente do {system_name}! 🤖 Estou aqui para tornar seus estudos mais eficientes. Posso explicar conceitos, criar questões, encontrar materiais e muito mais!",
                    "Olá! 👋 Sou seu assistente de estudos inteligente. Uso IA para responder suas dúvidas, gerar questões adaptadas e acompanhar seu progresso!",
                    "Sou parte do {system_name}! 🎓 Minha missão é ajudar você a aprender melhor através de explicações personalizadas e questões focadas no que você precisa!"
                ],

                MessageTypes.CLARIFICATION.value: [
                    "Entendo! 🤔 Deixe-me esclarecer isso para você. Sobre qual parte específica você tem dúvidas?",
                    "Sem problemas! 😊 Vou explicar de forma mais clara. O que exatamente não ficou claro?",
                    "Claro! 💡 Posso explicar melhor. Qual ponto específico você gostaria que eu detalhe mais?",
                    "Compreendo sua dúvida! 🧐 Vamos por partes. Qual aspecto você gostaria que eu explique primeiro?"
                ],

                MessageTypes.CASUAL.value: [
                    "Interessante! 😊 Posso ajudar você com alguma coisa relacionada aos estudos?",
                    "Legal! 👍 Já que estamos conversando, que tal aprendermos algo novo hoje?",
                    "Entendi! 😄 Aproveitando que você está aqui, posso ajudar com algum tópico de estudo?",
                    "Bacana! 🌟 Se quiser, posso sugerir algumas atividades de estudo interessantes!"
                ]
            },

            SupportedLanguages.ENGLISH.value: {
                MessageTypes.GREETING.value: [
                    "{time_greeting}! 😊 How can I help you today?",
                    "Hello! 👋 Ready to study today?",
                    "{time_greeting}! I'm here to help with your studies. What can I do for you?",
                    "Hi! 😄 Great to see you here! How can I help?",
                    "{time_greeting}, {user_name}! 🌟 Shall we study together today?",
                    "Hey there! 🔥 Ready to excel in your studies today?",
                    "Hello! 🚀 Time to learn amazing things!",
                    "Hi! ⚡ Great energy! Let's study hard today?",
                    "Hey, young scholar! 💪 Ready to transform knowledge into power?",
                    "Welcome! 🤗 I'm here to make your studies easier.",
                    "Hello, future expert! 🏆 Ready for another step towards success?",
                    "Hi there, champion! 🥇 Let's conquer more knowledge today?",
                    "Hello! 💎 Every question you ask is an investment in your bright future!",
                    "Greetings, dedicated student! 🌟 Shall we shine together?"
                ],

                MessageTypes.FAREWELL.value: [
                    "See you later! 👋 Keep studying and good luck!",
                    "Goodbye! 😊 Hope I helped. Come back anytime!",
                    "Thanks for using {system_name}! 🎓 Until next time!",
                    "Farewell! 🌟 Keep dedicating yourself to your studies!",
                    "See you! 📚 Success in your studies!",
                    "Go for it! 🚀 You're on the right path!",
                    "Until next time! 💪 Remember: every study counts!",
                    "Bye! 🎯 I trust in your potential, keep it up!",
                    "See you later! ⭐ You're building an incredible future!",
                    "Goodbye! 🔥 Keep that dedication, you'll go far!"
                ],

                MessageTypes.HELP.value: [
                    "Of course! 😊 I'm here to help with your studies. I can:\\n• Explain concepts\\n• Provide practice questions\\n• Find study materials\\n• Give study tips\\n\\nWhat would you like to do?",
                    "Absolutely! 🤝 I'm your study assistant. I can help with explanations, questions, references and much more. What do you need?",
                    "I'm here for that! 📚 I can explain concepts, create questions, find materials... Tell me what you want to study!",
                    "Let's go! 🚀 I can help with many things: answer doubts, practice with questions, find references... What do you have in mind?"
                ],

                MessageTypes.ERROR.value: [
                    "Oops! 😅 Something went wrong. Can you try again?",
                    "Sorry! 🤔 I had trouble processing that. Shall we try again?",
                    "Hmm! 😬 There was a small error. Please rephrase your question?",
                    "Oops! 🙃 Something didn't work as expected. Can you repeat in a different way?"
                ],

                MessageTypes.SUCCESS.value: [
                    "Perfect! ✅ We did it!",
                    "Excellent! 🎉 Everything worked out!",
                    "Great! 👍 It worked perfectly!",
                    "Success! 🌟 Mission accomplished!"
                ],

                MessageTypes.ENCOURAGEMENT.value: [
                    "You're doing great! 🌟 Keep it up and success is inevitable!",
                    "What incredible progress! 💪 I'm proud of your dedication!",
                    "Excellent! 🏆 Every step you take is a victory worth celebrating!",
                    "Congratulations! 🎉 Your persistence is inspiring!",
                    "Fantastic! ⚡ You're proving that dedication always pays off!",
                    "Wonderful! 🦋 Your evolution is visible and exciting!",
                    "Sensational! 🎯 You're building a bright future!"
                ],

                MessageTypes.STUDY_TIPS.value: [
                    "💡 Valuable tip: How about making a summary of what you learned today? It helps a lot with retention!",
                    "🎯 Smart strategy: Alternate different subjects - your brain will thank you!",
                    "⏰ Proven technique: Study for 25 minutes, rest for 5. It's the Pomodoro method!",
                    "📚 Expert secret: Teach someone what you learned - it's the best way to retain!",
                    "🧠 Mental hack: Connect new concepts with things you already know!",
                    "🌟 Pro tip: Celebrate your small victories - they motivate you for the big ones!",
                    "🔄 Ninja technique: Review the content after 1 day, 1 week and 1 month!"
                ],

                MessageTypes.ABOUT_SYSTEM.value: [
                    "I'm the {system_name} assistant! 🤖 I'm here to make your studies more efficient. I can explain concepts, create questions, find materials and much more!",
                    "Hello! 👋 I'm your intelligent study assistant. I use AI to answer your questions, generate adapted questions and track your progress!",
                    "I'm part of {system_name}! 🎓 My mission is to help you learn better through personalized explanations and questions focused on what you need!"
                ],

                MessageTypes.CLARIFICATION.value: [
                    "I understand! 🤔 Let me clarify that for you. Which specific part do you have questions about?",
                    "No problem! 😊 I'll explain more clearly. What exactly wasn't clear?",
                    "Sure! 💡 I can explain better. Which specific point would you like me to detail more?",
                    "I understand your doubt! 🧐 Let's go step by step. Which aspect would you like me to explain first?"
                ],

                MessageTypes.CASUAL.value: [
                    "Interesting! 😊 Can I help you with something related to studies?",
                    "Cool! 👍 Since we're talking, how about we learn something new today?",
                    "Got it! 😄 Since you're here, can I help with some study topic?",
                    "Nice! 🌟 If you want, I can suggest some interesting study activities!"
                ]
            },

            SupportedLanguages.SPANISH.value: {
                MessageTypes.GREETING.value: [
                    "¡{time_greeting}! 😊 ¿Cómo puedo ayudarte hoy?",
                    "¡Hola! 👋 ¿Listo para estudiar hoy?",
                    "¡{time_greeting}! Estoy aquí para ayudar con tus estudios. ¿En qué puedo ser útil?",
                    "¡Hola! 😄 ¡Qué bueno verte aquí! ¿Cómo puedo ayudar?",
                    "¡{time_greeting}, {user_name}! 🌟 ¿Vamos a estudiar juntos hoy?",
                    "¡Ey! 🔥 ¿Listo para destacar en los estudios hoy?",
                    "¡Hola! 🚀 ¡Es hora de aprender cosas increíbles!",
                    "¡Hola! ⚡ ¡Qué buena energía! ¿Vamos a estudiar con ganas hoy?",
                    "¡Bienvenido(a)! 🤗 Estoy aquí para hacer tus estudios más fáciles.",
                    "¡Hola, futuro(a) experto(a)! 🏆 ¿Listo para otro paso hacia el éxito?",
                    "¡Hola, campeón(ona)! 🥇 ¿Vamos a conquistar más conocimiento hoy?",
                    "¡Hola! 💎 ¡Cada pregunta tuya es una inversión en tu futuro brillante!",
                    "¡Saludos, estudiante dedicado(a)! 🌟 ¿Vamos a brillar juntos?"
                ],

                MessageTypes.FAREWELL.value: [
                    "¡Hasta luego! 👋 ¡Sigue estudiando y buena suerte!",
                    "¡Adiós! 😊 Espero haber ayudado. ¡Vuelve cuando quieras!",
                    "¡Gracias por usar {system_name}! 🎓 ¡Hasta la próxima!",
                    "¡Adiós! 🌟 ¡Sigue dedicándote a tus estudios!",
                    "¡Hasta más ver! 📚 ¡Éxito en tus estudios!",
                    "¡Dale con todo! 🚀 ¡Estás en el camino correcto!",
                    "¡Hasta la próxima! 💪 Recuerda: ¡cada estudio cuenta!",
                    "¡Chao! 🎯 ¡Confío en tu potencial, sigue así!",
                    "¡Hasta luego! ⭐ ¡Estás construyendo un futuro increíble!",
                    "¡Adiós! 🔥 ¡Mantén esa dedicación que llegarás lejos!"
                ],

                MessageTypes.HELP.value: [
                    "¡Por supuesto! 😊 Estoy aquí para ayudar con tus estudios. Puedo:\\n• Explicar conceptos\\n• Proporcionar preguntas para practicar\\n• Buscar materiales de estudio\\n• Dar consejos de estudio\\n\\n¿Qué te gustaría hacer?",
                    "¡Absolutamente! 🤝 Soy tu asistente de estudios. Puedo ayudar con explicaciones, preguntas, referencias y mucho más. ¿Qué necesitas?",
                    "¡Estoy aquí para eso! 📚 Puedo explicar conceptos, crear preguntas, encontrar materiales... ¡Cuéntame qué quieres estudiar!",
                    "¡Vamos! 🚀 Puedo ayudar con muchas cosas: resolver dudas, practicar con preguntas, encontrar referencias... ¿Qué tienes en mente?"
                ],

                MessageTypes.ERROR.value: [
                    "¡Ups! 😅 Parece que algo salió mal. ¿Puedes intentar de nuevo?",
                    "¡Perdón! 🤔 Tuve problemas para procesar eso. ¿Intentamos de nuevo?",
                    "¡Ay! 😬 Hubo un pequeño error. ¿Puedes reformular tu pregunta?",
                    "¡Ups! 🙃 Algo no funcionó como esperaba. ¿Puedes repetir de otra forma?"
                ],

                MessageTypes.SUCCESS.value: [
                    "¡Perfecto! ✅ ¡Lo logramos!",
                    "¡Excelente! 🎉 ¡Todo salió bien!",
                    "¡Genial! 👍 ¡Funcionó perfectamente!",
                    "¡Éxito! 🌟 ¡Misión cumplida!"
                ],

                MessageTypes.ENCOURAGEMENT.value: [
                    "¡Lo estás haciendo muy bien! 🌟 ¡Sigue así que el éxito es inevitable!",
                    "¡Qué progreso increíble! 💪 ¡Estoy orgulloso de tu dedicación!",
                    "¡Excelente! 🏆 ¡Cada paso tuyo es una victoria que merece ser celebrada!",
                    "¡Felicitaciones! 🎉 ¡Tu persistencia es inspiradora!",
                    "¡Fantástico! ⚡ ¡Estás demostrando que la dedicación siempre vale la pena!",
                    "¡Maravilloso! 🦋 ¡Tu evolución es visible y emocionante!",
                    "¡Sensacional! 🎯 ¡Estás construyendo un futuro brillante!"
                ],

                MessageTypes.STUDY_TIPS.value: [
                    "💡 Consejo valioso: ¿Qué tal hacer un resumen de lo que aprendiste hoy? ¡Ayuda mucho con la retención!",
                    "🎯 Estrategia inteligente: Alterna diferentes materias - ¡tu cerebro te lo agradecerá!",
                    "⏰ Técnica comprobada: Estudia por 25 minutos, descansa 5. ¡Es el método Pomodoro!",
                    "📚 Secreto de experto: Enseña a alguien lo que aprendiste - ¡es la mejor forma de retener!",
                    "🧠 Hack mental: ¡Conecta conceptos nuevos con cosas que ya sabes!",
                    "🌟 Consejo pro: Celebra tus pequeñas victorias - ¡te motivan para las grandes!",
                    "🔄 Técnica ninja: ¡Revisa el contenido después de 1 día, 1 semana y 1 mes!"
                ],

                MessageTypes.ABOUT_SYSTEM.value: [
                    "¡Soy el asistente de {system_name}! 🤖 Estoy aquí para hacer tus estudios más eficientes. ¡Puedo explicar conceptos, crear preguntas, encontrar materiales y mucho más!",
                    "¡Hola! 👋 Soy tu asistente de estudios inteligente. ¡Uso IA para responder tus preguntas, generar preguntas adaptadas y seguir tu progreso!",
                    "¡Soy parte de {system_name}! 🎓 ¡Mi misión es ayudarte a aprender mejor a través de explicaciones personalizadas y preguntas enfocadas en lo que necesitas!"
                ],

                MessageTypes.CLARIFICATION.value: [
                    "¡Entiendo! 🤔 Déjame aclarar eso para ti. ¿Sobre qué parte específica tienes dudas?",
                    "¡Sin problemas! 😊 Voy a explicar más claramente. ¿Qué exactamente no quedó claro?",
                    "¡Claro! 💡 Puedo explicar mejor. ¿Qué punto específico te gustaría que detalle más?",
                    "¡Comprendo tu duda! 🧐 Vamos por partes. ¿Qué aspecto te gustaría que explique primero?"
                ],

                MessageTypes.CASUAL.value: [
                    "¡Interesante! 😊 ¿Puedo ayudarte con algo relacionado con los estudios?",
                    "¡Genial! 👍 Ya que estamos conversando, ¿qué tal si aprendemos algo nuevo hoy?",
                    "¡Entiendo! 😄 Aprovechando que estás aquí, ¿puedo ayudar con algún tema de estudio?",
                    "¡Qué bueno! 🌟 Si quieres, ¡puedo sugerir algunas actividades de estudio interesantes!"
                ]
            },

            SupportedLanguages.FRENCH.value: {
                MessageTypes.GREETING.value: [
                    "{time_greeting} ! 😊 Comment puis-je vous aider aujourd'hui ?",
                    "Salut ! 👋 Prêt à étudier aujourd'hui ?",
                    "{time_greeting} ! Je suis là pour aider avec vos études. En quoi puis-je être utile ?",
                    "Salut ! 😄 Ravi de vous voir ici ! Comment puis-je aider ?",
                    "{time_greeting}, {user_name} ! 🌟 Allons-nous étudier ensemble aujourd'hui ?",
                    "Salut ! 🔥 Prêt à exceller dans vos études aujourd'hui ?",
                    "Bonjour ! 🚀 Il est temps d'apprendre des choses incroyables !",
                    "Salut ! ⚡ Quelle bonne énergie ! On étudie dur aujourd'hui ?",
                    "Bienvenue ! 🤗 Je suis là pour rendre vos études plus faciles.",
                    "Bonjour, futur expert ! 🏆 Prêt pour un autre pas vers le succès ?",
                    "Salut, champion ! 🥇 Allons conquérir plus de connaissances aujourd'hui ?",
                    "Bonjour ! 💎 Chaque question que vous posez est un investissement dans votre avenir brillant !",
                    "Salutations, étudiant dévoué ! 🌟 Allons-nous briller ensemble ?"
                ],

                MessageTypes.FAREWELL.value: [
                    "À bientôt ! 👋 Continuez à étudier et bonne chance !",
                    "Au revoir ! 😊 J'espère avoir aidé. Revenez quand vous voulez !",
                    "Merci d'utiliser {system_name} ! 🎓 À la prochaine !",
                    "Au revoir ! 🌟 Continuez à vous consacrer à vos études !",
                    "À plus tard ! 📚 Succès dans vos études !",
                    "Allez-y ! 🚀 Vous êtes sur la bonne voie !",
                    "À la prochaine ! 💪 Rappelez-vous : chaque étude compte !",
                    "Salut ! 🎯 Je fais confiance à votre potentiel, continuez ainsi !",
                    "À bientôt ! ⭐ Vous construisez un avenir incroyable !",
                    "Au revoir ! 🔥 Gardez cette dévotion, vous irez loin !"
                ],

                MessageTypes.HELP.value: [
                    "Bien sûr ! 😊 Je suis là pour aider avec vos études. Je peux :\\n• Expliquer des concepts\\n• Fournir des questions pour pratiquer\\n• Trouver des matériaux d'étude\\n• Donner des conseils d'étude\\n\\nQue souhaiteriez-vous faire ?",
                    "Absolument ! 🤝 Je suis votre assistant d'études. Je peux aider avec des explications, des questions, des références et bien plus. De quoi avez-vous besoin ?",
                    "Je suis là pour ça ! 📚 Je peux expliquer des concepts, créer des questions, trouver des matériaux... Dites-moi ce que vous voulez étudier !",
                    "Allons-y ! 🚀 Je peux aider avec beaucoup de choses : répondre aux doutes, pratiquer avec des questions, trouver des références... Qu'avez-vous en tête ?"
                ],

                MessageTypes.ERROR.value: [
                    "Oups ! 😅 Quelque chose s'est mal passé. Pouvez-vous réessayer ?",
                    "Désolé ! 🤔 J'ai eu du mal à traiter cela. Essayons encore ?",
                    "Hmm ! 😬 Il y a eu une petite erreur. Pouvez-vous reformuler votre question ?",
                    "Oups ! 🙃 Quelque chose n'a pas fonctionné comme prévu. Pouvez-vous répéter d'une autre façon ?"
                ],

                MessageTypes.SUCCESS.value: [
                    "Parfait ! ✅ Nous l'avons fait !",
                    "Excellent ! 🎉 Tout a marché !",
                    "Génial ! 👍 Ça a marché parfaitement !",
                    "Succès ! 🌟 Mission accomplie !"
                ],

                MessageTypes.ENCOURAGEMENT.value: [
                    "Vous vous en sortez très bien ! 🌟 Continuez ainsi et le succès est inévitable !",
                    "Quel progrès incroyable ! 💪 Je suis fier de votre dévouement !",
                    "Excellent ! 🏆 Chaque pas que vous faites est une victoire qui mérite d'être célébrée !",
                    "Félicitations ! 🎉 Votre persistance est inspirante !",
                    "Fantastique ! ⚡ Vous prouvez que le dévouement paie toujours !",
                    "Merveilleux ! 🦋 Votre évolution est visible et excitante !",
                    "Sensationnel ! 🎯 Vous construisez un avenir brillant !"
                ],

                MessageTypes.STUDY_TIPS.value: [
                    "💡 Conseil précieux : Que diriez-vous de faire un résumé de ce que vous avez appris aujourd'hui ? Cela aide beaucoup pour la rétention !",
                    "🎯 Stratégie intelligente : Alternez différentes matières - votre cerveau vous remerciera !",
                    "⏰ Technique éprouvée : Étudiez pendant 25 minutes, reposez-vous 5. C'est la méthode Pomodoro !",
                    "📚 Secret d'expert : Enseignez à quelqu'un ce que vous avez appris - c'est la meilleure façon de retenir !",
                    "🧠 Hack mental : Connectez les nouveaux concepts avec des choses que vous connaissez déjà !",
                    "🌟 Conseil pro : Célébrez vos petites victoires - elles vous motivent pour les grandes !",
                    "🔄 Technique ninja : Révisez le contenu après 1 jour, 1 semaine et 1 mois !"
                ],

                MessageTypes.ABOUT_SYSTEM.value: [
                    "Je suis l'assistant de {system_name} ! 🤖 Je suis là pour rendre vos études plus efficaces. Je peux expliquer des concepts, créer des questions, trouver des matériaux et bien plus !",
                    "Salut ! 👋 Je suis votre assistant d'études intelligent. J'utilise l'IA pour répondre à vos questions, générer des questions adaptées et suivre vos progrès !",
                    "Je fais partie de {system_name} ! 🎓 Ma mission est de vous aider à mieux apprendre grâce à des explications personnalisées et des questions ciblées sur ce dont vous avez besoin !"
                ],

                MessageTypes.CLARIFICATION.value: [
                    "Je comprends ! 🤔 Laissez-moi clarifier cela pour vous. Sur quelle partie spécifique avez-vous des questions ?",
                    "Pas de problème ! 😊 Je vais expliquer plus clairement. Qu'est-ce qui n'était pas exactement clair ?",
                    "Bien sûr ! 💡 Je peux mieux expliquer. Quel point spécifique aimeriez-vous que je détaille davantage ?",
                    "Je comprends votre doute ! 🧐 Allons-y étape par étape. Quel aspect aimeriez-vous que j'explique en premier ?"
                ],

                MessageTypes.CASUAL.value: [
                    "Intéressant ! 😊 Puis-je vous aider avec quelque chose lié aux études ?",
                    "Cool ! 👍 Puisqu'on discute, que diriez-vous d'apprendre quelque chose de nouveau aujourd'hui ?",
                    "Compris ! 😄 Puisque vous êtes là, puis-je aider avec un sujet d'étude ?",
                    "Sympa ! 🌟 Si vous voulez, je peux suggérer des activités d'étude intéressantes !"
                ]
            }
        }

    def get_message(
        self,
        language: str,
        message_type: str,
        **kwargs
    ) -> str:
        """Get a localized message."""
        messages = self.messages.get(language, {}).get(message_type, [])

        if not messages:
            # Fallback to Portuguese if not found
            messages = self.messages.get(SupportedLanguages.PORTUGUESE.value, {}).get(message_type, [])

        if not messages:
            return f"Message not found: {message_type}"

        # Select random message
        template = random.choice(messages)

        # Replace placeholders
        return self._format_message(template, **kwargs)

    def _format_message(self, template: str, **kwargs) -> str:
        """Format message with provided variables."""
        # Get time greeting
        now = datetime.now()
        hour = now.hour

        time_greetings = {
            SupportedLanguages.PORTUGUESE.value: {
                'morning': 'Bom dia',
                'afternoon': 'Boa tarde',
                'evening': 'Boa noite'
            },
            SupportedLanguages.ENGLISH.value: {
                'morning': 'Good morning',
                'afternoon': 'Good afternoon',
                'evening': 'Good evening'
            },
            SupportedLanguages.SPANISH.value: {
                'morning': 'Buenos días',
                'afternoon': 'Buenas tardes',
                'evening': 'Buenas noches'
            },
            SupportedLanguages.FRENCH.value: {
                'morning': 'Bonjour',
                'afternoon': 'Bon après-midi',
                'evening': 'Bonsoir'
            }
        }

        language = kwargs.get('language', SupportedLanguages.PORTUGUESE.value)
        greetings = time_greetings.get(language, time_greetings[SupportedLanguages.PORTUGUESE.value])

        if 6 <= hour < 12:
            time_greeting = greetings['morning']
        elif 12 <= hour < 18:
            time_greeting = greetings['afternoon']
        else:
            time_greeting = greetings['evening']

        # Default replacements
        replacements = {
            'time_greeting': time_greeting,
            'user_name': kwargs.get('user_name', 'noivo(a)'),
            'system_name': kwargs.get('system_name', 'Marriplan'),
            **kwargs
        }

        # Apply replacements
        formatted = template
        for key, value in replacements.items():
            formatted = formatted.replace(f'{{{key}}}', str(value))

        return formatted

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return [lang.value for lang in SupportedLanguages]

    def has_language_support(self, language: str) -> bool:
        """Check if language is supported."""
        return language in self.messages