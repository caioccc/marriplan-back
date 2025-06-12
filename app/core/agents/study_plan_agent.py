"""
Study Plan Agent - Especializado em criar e gerenciar planos de estudo personalizados.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from app.core.agents.base import BaseAgent, AgentResponse, AgentCapability
from app.core.models.agent_models import AgentRequest
from app.core.services.intent_detection import IntentType
from app.core.services.progress_tracking import ProgressTrackingService, LearningActivity, LearningGoal
from app.core.services.recommendation_engine import RecommendationEngine, UserProfile
from app.core.i18n import LocalizationManager, PatternManager, SupportedLanguages, MessageTypes

logger = logging.getLogger(__name__)


class StudyPlanType(Enum):
    """Tipos de planos de estudo."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    EXAM_PREP = "exam_prep"
    SUBJECT_MASTERY = "subject_mastery"
    SKILL_BUILDING = "skill_building"
    REVIEW_PLAN = "review_plan"


class StudyPlanPriority(Enum):
    """Prioridades do plano de estudo."""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class StudySession:
    """Representa uma sessão de estudo no plano."""
    session_id: str
    title: str
    description: str
    subject_area: str
    topics: List[str]
    estimated_duration_minutes: int
    difficulty_level: str
    activities: List[str]  # ['questions', 'reading', 'practice', 'review']
    prerequisites: List[str]
    learning_objectives: List[str]
    resources: List[str]
    is_completed: bool = False
    completion_date: Optional[datetime] = None
    actual_duration_minutes: Optional[int] = None


@dataclass
class StudyPlan:
    """Representa um plano de estudo completo."""
    plan_id: str
    user_id: str
    title: str
    description: str
    plan_type: StudyPlanType
    priority: StudyPlanPriority
    subjects: List[str]
    total_duration_days: int
    estimated_hours_per_day: float
    start_date: datetime
    end_date: datetime
    sessions: List[StudySession]
    goals: List[str]
    progress_percentage: float = 0.0
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StudyPlanAgent(BaseAgent):
    """
    Agent especializado em criar e gerenciar planos de estudo personalizados.
    
    Responsável por:
    - Criação de planos de estudo personalizados
    - Acompanhamento de progresso dos planos
    - Ajustes dinâmicos baseados na performance
    - Recomendações de melhorias no plano
    - Integração com outros agentes
    """
    
    def __init__(self):
        """Inicializa o Study Plan Agent."""
        super().__init__(
            name="StudyPlanAgent",
            capabilities=[
                AgentCapability.STUDY_PLANNING,
                AgentCapability.PROGRESS_TRACKING,
                AgentCapability.RECOMMENDATION
            ],
            priority=85  # Alta prioridade para planejamento
        )
        
        # Internationalization support
        self.localization = LocalizationManager()
        self.patterns = PatternManager()
        
        # Integração com outros serviços
        self.progress_tracker = ProgressTrackingService()
        self.recommendation_engine = RecommendationEngine()
        
        # Storage simulado - em produção seria banco de dados
        self.study_plans = {}  # user_id -> List[StudyPlan]
        self.plan_templates = self._load_plan_templates()
        
        # Configurações
        self.config = {
            'max_plans_per_user': 5,
            'default_session_duration': 45,
            'min_session_duration': 15,
            'max_session_duration': 120,
            'default_study_hours_per_day': 2.0,
            'plan_adjustment_threshold': 0.3,  # Limiar para ajustes automáticos
            'auto_adjust_enabled': True,
            'progress_check_interval_days': 3
        }
        
        logger.info("Study Plan Agent inicializado")
    
    def can_handle(self, request: AgentRequest) -> bool:
        """Verifica se o agente pode processar a requisição."""
        
        # Verificar intent
        intent_data = request.metadata.get('intent', {})
        intent_type = intent_data.get('type', '')
        
        # Intents que o Study Plan Agent pode processar
        planning_intents = {
            IntentType.STUDY_PLAN.value,
            'create_plan',
            'update_plan',
            'plan_progress',
            'study_schedule'
        }
        
        if intent_type in planning_intents:
            return True
        
        # Detect language and check patterns
        content = request.content or request.message
        language = self.patterns.detect_language(content)
        
        # Check for planning keywords
        planning_keywords = self._get_planning_keywords(language)
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in planning_keywords):
            return True
        
        return False
    
    def _get_planning_keywords(self, language: str) -> List[str]:
        """Obtém palavras-chave de planejamento por idioma."""
        
        keywords_by_language = {
            SupportedLanguages.PORTUGUESE.value: [
                'plano de estudo', 'cronograma', 'planejamento', 'organizar estudos',
                'rotina de estudo', 'horário', 'agenda', 'preparação'
            ],
            SupportedLanguages.ENGLISH.value: [
                'study plan', 'schedule', 'planning', 'organize studies',
                'study routine', 'timetable', 'agenda', 'preparation'
            ],
            SupportedLanguages.SPANISH.value: [
                'plan de estudio', 'horario', 'planificación', 'organizar estudios',
                'rutina de estudio', 'cronograma', 'agenda', 'preparación'
            ],
            SupportedLanguages.FRENCH.value: [
                'plan d\'étude', 'horaire', 'planification', 'organiser études',
                'routine d\'étude', 'emploi du temps', 'agenda', 'préparation'
            ]
        }
        
        return keywords_by_language.get(language, keywords_by_language[SupportedLanguages.PORTUGUESE.value])
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """Processa a requisição de planejamento de estudos."""
        
        try:
            # Detectar idioma
            content = request.content or request.message
            language = self.patterns.detect_language(content)
            
            # Analisar tipo de requisição
            request_type = self._analyze_request_type(content, language)
            
            # Processar baseado no tipo
            if request_type == 'create_plan':
                response_content = await self._handle_create_plan(request, language)
            elif request_type == 'view_progress':
                response_content = await self._handle_view_progress(request, language)
            elif request_type == 'update_plan':
                response_content = await self._handle_update_plan(request, language)
            elif request_type == 'get_recommendations':
                response_content = await self._handle_get_recommendations(request, language)
            else:
                response_content = await self._handle_general_planning(request, language)
            
            # Calcular confiança
            confidence = self._calculate_confidence(request_type, request)
            
            # Metadata da resposta
            metadata = {
                'request_type': request_type,
                'language': language,
                'user_id': request.user_id or 'anonymous'
            }
            
            return AgentResponse(
                agent_name=self.name,
                content=response_content,
                confidence=confidence,
                metadata=metadata
            )
        
        except Exception as e:
            logger.error(f"Erro no processamento do plano de estudos: {e}")
            return AgentResponse(
                agent_name=self.name,
                content=self._get_error_message(language),
                confidence=0.3,
                metadata={'error': str(e), 'language': language}
            )
    
    def _analyze_request_type(self, content: str, language: str) -> str:
        """Analisa o tipo de requisição de planejamento."""
        
        content_lower = content.lower()
        
        # Padrões por tipo de requisição
        type_patterns = {
            'create_plan': {
                SupportedLanguages.PORTUGUESE.value: ['criar plano', 'novo plano', 'fazer cronograma', 'organizar estudos'],
                SupportedLanguages.ENGLISH.value: ['create plan', 'new plan', 'make schedule', 'organize studies'],
                SupportedLanguages.SPANISH.value: ['crear plan', 'nuevo plan', 'hacer cronograma', 'organizar estudios'],
                SupportedLanguages.FRENCH.value: ['créer plan', 'nouveau plan', 'faire horaire', 'organiser études']
            },
            'view_progress': {
                SupportedLanguages.PORTUGUESE.value: ['progresso', 'andamento', 'como estou', 'meu progresso'],
                SupportedLanguages.ENGLISH.value: ['progress', 'how am i', 'my progress', 'advancement'],
                SupportedLanguages.SPANISH.value: ['progreso', 'avance', 'cómo estoy', 'mi progreso'],
                SupportedLanguages.FRENCH.value: ['progrès', 'avancement', 'comment je vais', 'mon progrès']
            },
            'update_plan': {
                SupportedLanguages.PORTUGUESE.value: ['atualizar plano', 'modificar', 'ajustar cronograma'],
                SupportedLanguages.ENGLISH.value: ['update plan', 'modify', 'adjust schedule'],
                SupportedLanguages.SPANISH.value: ['actualizar plan', 'modificar', 'ajustar cronograma'],
                SupportedLanguages.FRENCH.value: ['mettre à jour plan', 'modifier', 'ajuster horaire']
            },
            'get_recommendations': {
                SupportedLanguages.PORTUGUESE.value: ['recomendações', 'sugestões', 'o que estudar'],
                SupportedLanguages.ENGLISH.value: ['recommendations', 'suggestions', 'what to study'],
                SupportedLanguages.SPANISH.value: ['recomendaciones', 'sugerencias', 'qué estudiar'],
                SupportedLanguages.FRENCH.value: ['recommandations', 'suggestions', 'quoi étudier']
            }
        }
        
        for req_type, patterns in type_patterns.items():
            lang_patterns = patterns.get(language, patterns[SupportedLanguages.PORTUGUESE.value])
            if any(pattern in content_lower for pattern in lang_patterns):
                return req_type
        
        return 'general_planning'
    
    async def _handle_create_plan(self, request: AgentRequest, language: str) -> str:
        """Lida com requisições de criação de plano."""
        
        user_id = request.user_id or request.session_id
        content = request.content or request.message
        
        # Extrair informações do pedido
        plan_info = self._extract_plan_requirements(content, language)
        
        # Criar plano personalizado
        study_plan = await self._create_personalized_plan(user_id, plan_info, language)
        
        if study_plan:
            # Salvar plano
            if user_id not in self.study_plans:
                self.study_plans[user_id] = []
            
            self.study_plans[user_id].append(study_plan)
            
            # Formatar resposta
            return self._format_plan_response(study_plan, language)
        else:
            return self._get_plan_creation_error(language)
    
    async def _handle_view_progress(self, request: AgentRequest, language: str) -> str:
        """Lida com requisições de visualização de progresso."""
        
        user_id = request.user_id or request.session_id
        
        # Obter planos do usuário
        user_plans = self.study_plans.get(user_id, [])
        
        if not user_plans:
            return self._get_no_plans_message(language)
        
        # Obter progresso do usuário
        progress = self.progress_tracker.get_user_progress(user_id)
        
        # Formatar resposta de progresso
        return self._format_progress_response(user_plans, progress, language)
    
    async def _handle_update_plan(self, request: AgentRequest, language: str) -> str:
        """Lida com requisições de atualização de plano."""
        
        user_id = request.user_id or request.session_id
        
        # Obter planos ativos
        user_plans = self.study_plans.get(user_id, [])
        active_plans = [p for p in user_plans if p.is_active]
        
        if not active_plans:
            return self._get_no_active_plans_message(language)
        
        # Analisar progresso e fazer ajustes
        updated_plans = []
        for plan in active_plans:
            updated_plan = await self._adjust_plan_based_on_progress(plan, user_id)
            updated_plans.append(updated_plan)
        
        return self._format_plan_update_response(updated_plans, language)
    
    async def _handle_get_recommendations(self, request: AgentRequest, language: str) -> str:
        """Lida com requisições de recomendações de estudo."""
        
        user_id = request.user_id or request.session_id
        
        # Obter recomendações personalizadas
        recommendations = self.recommendation_engine.get_recommendations(user_id)
        
        if not recommendations:
            return self._get_no_recommendations_message(language)
        
        return self._format_recommendations_response(recommendations, language)
    
    async def _handle_general_planning(self, request: AgentRequest, language: str) -> str:
        """Lida com requisições gerais de planejamento."""
        
        # Resposta geral sobre planejamento de estudos
        return self._get_general_planning_advice(language)
    
    def _extract_plan_requirements(self, content: str, language: str) -> Dict[str, Any]:
        """Extrai requisitos do plano a partir do conteúdo."""
        
        # Análise básica do conteúdo
        content_lower = content.lower()
        
        # Detectar matérias mencionadas
        subjects = []
        subject_keywords = {
            'matemática': ['matemática', 'math', 'cálculo', 'álgebra'],
            'física': ['física', 'physics', 'mecânica'],
            'química': ['química', 'chemistry', 'reações'],
            'biologia': ['biologia', 'biology', 'vida'],
            'história': ['história', 'history'],
            'geografia': ['geografia', 'geography']
        }
        
        for subject, keywords in subject_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                subjects.append(subject)
        
        # Detectar duração
        duration_days = 30  # default
        if 'semana' in content_lower or 'week' in content_lower:
            duration_days = 7
        elif 'mês' in content_lower or 'month' in content_lower:
            duration_days = 30
        elif 'dia' in content_lower or 'day' in content_lower:
            duration_days = 1
        
        # Detectar intensidade
        hours_per_day = 2.0  # default
        if 'intensivo' in content_lower or 'intensive' in content_lower:
            hours_per_day = 4.0
        elif 'leve' in content_lower or 'light' in content_lower:
            hours_per_day = 1.0
        
        return {
            'subjects': subjects if subjects else ['geral'],
            'duration_days': duration_days,
            'hours_per_day': hours_per_day,
            'language': language
        }
    
    async def _create_personalized_plan(
        self, 
        user_id: str, 
        plan_info: Dict[str, Any], 
        language: str
    ) -> Optional[StudyPlan]:
        """Cria um plano de estudo personalizado."""
        
        try:
            # Obter progresso do usuário para personalização
            progress = self.progress_tracker.get_user_progress(user_id)
            
            # Selecionar template apropriado
            template = self._select_plan_template(plan_info, progress)
            
            # Criar sessões de estudo
            sessions = self._create_study_sessions(plan_info, template, language)
            
            # Criar plano
            plan = StudyPlan(
                plan_id=f"plan_{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                title=self._generate_plan_title(plan_info, language),
                description=self._generate_plan_description(plan_info, language),
                plan_type=StudyPlanType.WEEKLY,  # Default
                priority=StudyPlanPriority.MEDIUM,
                subjects=plan_info['subjects'],
                total_duration_days=plan_info['duration_days'],
                estimated_hours_per_day=plan_info['hours_per_day'],
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=plan_info['duration_days']),
                sessions=sessions,
                goals=self._generate_study_goals(plan_info, language)
            )
            
            return plan
        
        except Exception as e:
            logger.error(f"Erro ao criar plano personalizado: {e}")
            return None
    
    def _select_plan_template(self, plan_info: Dict[str, Any], progress: Any) -> Dict[str, Any]:
        """Seleciona template de plano apropriado."""
        
        # Lógica simplificada - em produção seria mais sofisticada
        if plan_info['duration_days'] <= 7:
            return self.plan_templates['weekly']
        elif plan_info['duration_days'] <= 30:
            return self.plan_templates['monthly']
        else:
            return self.plan_templates['long_term']
    
    def _create_study_sessions(
        self, 
        plan_info: Dict[str, Any], 
        template: Dict[str, Any], 
        language: str
    ) -> List[StudySession]:
        """Cria sessões de estudo para o plano."""
        
        sessions = []
        subjects = plan_info['subjects']
        duration_days = plan_info['duration_days']
        session_duration = self.config['default_session_duration']
        
        # Distribuir sessões ao longo dos dias
        sessions_per_day = max(1, int(plan_info['hours_per_day'] * 60 / session_duration))
        
        for day in range(duration_days):
            for session_num in range(sessions_per_day):
                subject = subjects[session_num % len(subjects)]
                
                session = StudySession(
                    session_id=f"session_{day}_{session_num}",
                    title=self._generate_session_title(subject, day + 1, language),
                    description=self._generate_session_description(subject, language),
                    subject_area=subject,
                    topics=self._get_topics_for_subject(subject),
                    estimated_duration_minutes=session_duration,
                    difficulty_level='intermediate',
                    activities=['reading', 'practice', 'review'],
                    prerequisites=[],
                    learning_objectives=self._get_learning_objectives(subject, language),
                    resources=self._get_subject_resources(subject)
                )
                
                sessions.append(session)
        
        return sessions
    
    def _generate_plan_title(self, plan_info: Dict[str, Any], language: str) -> str:
        """Gera título para o plano."""
        
        subjects_str = ', '.join(plan_info['subjects'])
        duration = plan_info['duration_days']
        
        title_templates = {
            SupportedLanguages.PORTUGUESE.value: f"Plano de {duration} dias - {subjects_str.title()}",
            SupportedLanguages.ENGLISH.value: f"{duration}-day Plan - {subjects_str.title()}",
            SupportedLanguages.SPANISH.value: f"Plan de {duration} días - {subjects_str.title()}",
            SupportedLanguages.FRENCH.value: f"Plan de {duration} jours - {subjects_str.title()}"
        }
        
        return title_templates.get(language, title_templates[SupportedLanguages.PORTUGUESE.value])
    
    def _generate_plan_description(self, plan_info: Dict[str, Any], language: str) -> str:
        """Gera descrição para o plano."""
        
        hours = plan_info['hours_per_day']
        subjects = ', '.join(plan_info['subjects'])
        
        desc_templates = {
            SupportedLanguages.PORTUGUESE.value: f"Plano personalizado com {hours}h diárias focando em {subjects}.",
            SupportedLanguages.ENGLISH.value: f"Personalized plan with {hours}h daily focusing on {subjects}.",
            SupportedLanguages.SPANISH.value: f"Plan personalizado con {hours}h diarias enfocándose en {subjects}.",
            SupportedLanguages.FRENCH.value: f"Plan personnalisé avec {hours}h par jour axé sur {subjects}."
        }
        
        return desc_templates.get(language, desc_templates[SupportedLanguages.PORTUGUESE.value])
    
    def _generate_study_goals(self, plan_info: Dict[str, Any], language: str) -> List[str]:
        """Gera objetivos de estudo."""
        
        goals_templates = {
            SupportedLanguages.PORTUGUESE.value: [
                "Melhorar compreensão dos conceitos fundamentais",
                "Aumentar taxa de acerto nas questões",
                "Manter consistência nos estudos diários"
            ],
            SupportedLanguages.ENGLISH.value: [
                "Improve understanding of fundamental concepts",
                "Increase accuracy rate in questions",
                "Maintain consistency in daily studies"
            ],
            SupportedLanguages.SPANISH.value: [
                "Mejorar comprensión de conceptos fundamentales",
                "Aumentar tasa de acierto en preguntas",
                "Mantener consistencia en estudios diarios"
            ],
            SupportedLanguages.FRENCH.value: [
                "Améliorer la compréhension des concepts fondamentaux",
                "Augmenter le taux de réussite aux questions",
                "Maintenir la cohérence dans les études quotidiennes"
            ]
        }
        
        return goals_templates.get(language, goals_templates[SupportedLanguages.PORTUGUESE.value])
    
    def _generate_session_title(self, subject: str, day: int, language: str) -> str:
        """Gera título para sessão."""
        
        title_templates = {
            SupportedLanguages.PORTUGUESE.value: f"Dia {day}: {subject.title()}",
            SupportedLanguages.ENGLISH.value: f"Day {day}: {subject.title()}",
            SupportedLanguages.SPANISH.value: f"Día {day}: {subject.title()}",
            SupportedLanguages.FRENCH.value: f"Jour {day}: {subject.title()}"
        }
        
        return title_templates.get(language, title_templates[SupportedLanguages.PORTUGUESE.value])
    
    def _generate_session_description(self, subject: str, language: str) -> str:
        """Gera descrição para sessão."""
        
        desc_templates = {
            SupportedLanguages.PORTUGUESE.value: f"Sessão focada em {subject} com teoria e prática.",
            SupportedLanguages.ENGLISH.value: f"Session focused on {subject} with theory and practice.",
            SupportedLanguages.SPANISH.value: f"Sesión enfocada en {subject} con teoría y práctica.",
            SupportedLanguages.FRENCH.value: f"Session axée sur {subject} avec théorie et pratique."
        }
        
        return desc_templates.get(language, desc_templates[SupportedLanguages.PORTUGUESE.value])
    
    def _get_topics_for_subject(self, subject: str) -> List[str]:
        """Obtém tópicos para uma matéria."""
        
        topics_map = {
            'matemática': ['números', 'álgebra', 'geometria'],
            'física': ['mecânica', 'energia', 'ondas'],
            'química': ['átomos', 'ligações', 'reações'],
            'biologia': ['células', 'genética', 'evolução'],
            'história': ['antiguidade', 'medieval', 'moderna'],
            'geografia': ['físico', 'humano', 'econômico']
        }
        
        return topics_map.get(subject, ['conceitos básicos'])
    
    def _get_learning_objectives(self, subject: str, language: str) -> List[str]:
        """Obtém objetivos de aprendizado para uma matéria."""
        
        objectives_templates = {
            SupportedLanguages.PORTUGUESE.value: {
                'matemática': ['Resolver equações básicas', 'Compreender funções'],
                'física': ['Entender movimento', 'Calcular energia'],
                'química': ['Identificar elementos', 'Balancear reações']
            },
            SupportedLanguages.ENGLISH.value: {
                'mathematics': ['Solve basic equations', 'Understand functions'],
                'physics': ['Understand motion', 'Calculate energy'],
                'chemistry': ['Identify elements', 'Balance reactions']
            }
        }
        
        lang_objectives = objectives_templates.get(language, objectives_templates[SupportedLanguages.PORTUGUESE.value])
        return lang_objectives.get(subject, ['Compreender conceitos básicos'])
    
    def _get_subject_resources(self, subject: str) -> List[str]:
        """Obtém recursos para uma matéria."""
        
        return [
            f"Livro didático de {subject}",
            f"Exercícios online de {subject}",
            f"Videoaulas de {subject}"
        ]
    
    async def _adjust_plan_based_on_progress(self, plan: StudyPlan, user_id: str) -> StudyPlan:
        """Ajusta plano baseado no progresso do usuário."""
        
        if not self.config['auto_adjust_enabled']:
            return plan
        
        try:
            # Obter progresso atual
            progress = self.progress_tracker.get_user_progress(user_id)
            
            if not progress:
                return plan
            
            # Analisar se ajustes são necessários
            if progress.correct_percentage < 50:
                # Performance baixa - reduzir dificuldade
                for session in plan.sessions:
                    if not session.is_completed:
                        session.difficulty_level = 'basic'
                        session.estimated_duration_minutes = max(
                            session.estimated_duration_minutes - 10,
                            self.config['min_session_duration']
                        )
            
            elif progress.correct_percentage > 80:
                # Performance alta - aumentar desafio
                for session in plan.sessions:
                    if not session.is_completed:
                        session.difficulty_level = 'advanced'
                        session.estimated_duration_minutes = min(
                            session.estimated_duration_minutes + 15,
                            self.config['max_session_duration']
                        )
            
            # Atualizar progresso do plano
            completed_sessions = sum(1 for s in plan.sessions if s.is_completed)
            plan.progress_percentage = (completed_sessions / len(plan.sessions)) * 100
            plan.last_updated = datetime.now()
            
            return plan
        
        except Exception as e:
            logger.error(f"Erro ao ajustar plano: {e}")
            return plan
    
    def _format_plan_response(self, plan: StudyPlan, language: str) -> str:
        """Formata resposta com o plano criado."""
        
        response_templates = {
            SupportedLanguages.PORTUGUESE.value: f"""
📚 **Plano de Estudos Criado!**

**{plan.title}**
{plan.description}

📅 **Duração:** {plan.total_duration_days} dias
⏰ **Tempo diário:** {plan.estimated_hours_per_day}h
📖 **Matérias:** {', '.join(plan.subjects)}

**🎯 Objetivos:**
{chr(10).join(f'• {goal}' for goal in plan.goals)}

**📋 Primeiras sessões:**
{chr(10).join(f'• {session.title} ({session.estimated_duration_minutes}min)' for session in plan.sessions[:3])}

Seu plano está pronto! Comece quando quiser e acompanhe seu progresso. 🚀
""",

            SupportedLanguages.ENGLISH.value: f"""
📚 **Study Plan Created!**

**{plan.title}**
{plan.description}

📅 **Duration:** {plan.total_duration_days} days
⏰ **Daily time:** {plan.estimated_hours_per_day}h
📖 **Subjects:** {', '.join(plan.subjects)}

**🎯 Goals:**
{chr(10).join(f'• {goal}' for goal in plan.goals)}

**📋 First sessions:**
{chr(10).join(f'• {session.title} ({session.estimated_duration_minutes}min)' for session in plan.sessions[:3])}

Your plan is ready! Start whenever you want and track your progress. 🚀
"""
        }
        
        return response_templates.get(language, response_templates[SupportedLanguages.PORTUGUESE.value])
    
    def _format_progress_response(self, plans: List[StudyPlan], progress: Any, language: str) -> str:
        """Formata resposta de progresso."""
        
        active_plans = [p for p in plans if p.is_active]
        
        if not active_plans:
            no_plans_msg = {
                SupportedLanguages.PORTUGUESE.value: "Você não tem planos ativos no momento.",
                SupportedLanguages.ENGLISH.value: "You don't have any active plans right now."
            }
            return no_plans_msg.get(language, no_plans_msg[SupportedLanguages.PORTUGUESE.value])
        
        plan = active_plans[0]  # Mostrar primeiro plano ativo
        
        response_templates = {
            SupportedLanguages.PORTUGUESE.value: f"""
📊 **Progresso do Seu Plano de Estudos**

**{plan.title}**
📈 Progresso: {plan.progress_percentage:.1f}%
📅 Criado: {plan.created_at.strftime('%d/%m/%Y')}

**📚 Estatísticas Gerais:**
• Atividades concluídas: {progress.total_activities if progress else 0}
• Taxa de acerto: {progress.correct_percentage:.1f}% if progress else 'N/A'
• Tempo de estudo: {progress.study_time_minutes if progress else 0} minutos
• Sequência atual: {progress.current_streak if progress else 0} dias

**🎯 Próximas sessões:**
{chr(10).join(f'• {session.title}' for session in plan.sessions if not session.is_completed)[:3]}

Continue assim! Você está no caminho certo! 💪
""",

            SupportedLanguages.ENGLISH.value: f"""
📊 **Your Study Plan Progress**

**{plan.title}**
📈 Progress: {plan.progress_percentage:.1f}%
📅 Created: {plan.created_at.strftime('%m/%d/%Y')}

**📚 General Statistics:**
• Activities completed: {progress.total_activities if progress else 0}
• Accuracy rate: {progress.correct_percentage:.1f}% if progress else 'N/A'
• Study time: {progress.study_time_minutes if progress else 0} minutes
• Current streak: {progress.current_streak if progress else 0} days

**🎯 Next sessions:**
{chr(10).join(f'• {session.title}' for session in plan.sessions if not session.is_completed)[:3]}

Keep it up! You're on the right track! 💪
"""
        }
        
        return response_templates.get(language, response_templates[SupportedLanguages.PORTUGUESE.value])
    
    def _format_plan_update_response(self, plans: List[StudyPlan], language: str) -> str:
        """Formata resposta de atualização de plano."""
        
        update_msg = {
            SupportedLanguages.PORTUGUESE.value: f"""
🔄 **Planos Atualizados!**

Seus planos foram ajustados baseado no seu progresso:

{chr(10).join(f'• {plan.title} - {plan.progress_percentage:.1f}% concluído' for plan in plans)}

As próximas sessões foram otimizadas para seu nível atual. Continue estudando! 📚
""",
            SupportedLanguages.ENGLISH.value: f"""
🔄 **Plans Updated!**

Your plans have been adjusted based on your progress:

{chr(10).join(f'• {plan.title} - {plan.progress_percentage:.1f}% completed' for plan in plans)}

Next sessions have been optimized for your current level. Keep studying! 📚
"""
        }
        
        return update_msg.get(language, update_msg[SupportedLanguages.PORTUGUESE.value])
    
    def _format_recommendations_response(self, recommendations: List, language: str) -> str:
        """Formata resposta de recomendações."""
        
        rec_msg = {
            SupportedLanguages.PORTUGUESE.value: f"""
💡 **Recomendações Personalizadas**

Baseado no seu perfil, recomendo:

{chr(10).join(f'• {rec.title}: {rec.description}' for rec in recommendations[:3])}

Essas recomendações foram criadas especificamente para você! 🎯
""",
            SupportedLanguages.ENGLISH.value: f"""
💡 **Personalized Recommendations**

Based on your profile, I recommend:

{chr(10).join(f'• {rec.title}: {rec.description}' for rec in recommendations[:3])}

These recommendations were created specifically for you! 🎯
"""
        }
        
        return rec_msg.get(language, rec_msg[SupportedLanguages.PORTUGUESE.value])
    
    def _load_plan_templates(self) -> Dict[str, Dict[str, Any]]:
        """Carrega templates de planos de estudo."""
        
        return {
            'weekly': {
                'sessions_per_day': 2,
                'session_duration': 45,
                'difficulty_progression': ['basic', 'intermediate'],
                'focus': 'consistency'
            },
            'monthly': {
                'sessions_per_day': 3,
                'session_duration': 50,
                'difficulty_progression': ['basic', 'intermediate', 'advanced'],
                'focus': 'comprehensive'
            },
            'long_term': {
                'sessions_per_day': 2,
                'session_duration': 60,
                'difficulty_progression': ['basic', 'intermediate', 'advanced', 'expert'],
                'focus': 'mastery'
            }
        }
    
    def _calculate_confidence(self, request_type: str, request: AgentRequest) -> float:
        """Calcula confiança na resposta."""
        
        confidence_map = {
            'create_plan': 0.9,
            'view_progress': 0.85,
            'update_plan': 0.8,
            'get_recommendations': 0.75,
            'general_planning': 0.7
        }
        
        return confidence_map.get(request_type, 0.6)
    
    def _get_error_message(self, language: str) -> str:
        """Obtém mensagem de erro baseada no idioma."""
        
        error_messages = {
            SupportedLanguages.PORTUGUESE.value: "Desculpe, tive dificuldades para criar seu plano de estudos. Pode tentar novamente?",
            SupportedLanguages.ENGLISH.value: "Sorry, I had trouble creating your study plan. Could you try again?",
            SupportedLanguages.SPANISH.value: "Disculpa, tuve dificultades para crear tu plan de estudios. ¿Podrías intentar de nuevo?",
            SupportedLanguages.FRENCH.value: "Désolé, j'ai eu du mal à créer votre plan d'étude. Pourriez-vous essayer à nouveau?"
        }
        
        return error_messages.get(language, error_messages[SupportedLanguages.PORTUGUESE.value])
    
    def _get_no_plans_message(self, language: str) -> str:
        """Mensagem quando não há planos."""
        
        messages = {
            SupportedLanguages.PORTUGUESE.value: "Você ainda não tem planos de estudo. Que tal criarmos um agora?",
            SupportedLanguages.ENGLISH.value: "You don't have any study plans yet. How about we create one now?"
        }
        
        return messages.get(language, messages[SupportedLanguages.PORTUGUESE.value])
    
    def _get_no_active_plans_message(self, language: str) -> str:
        """Mensagem quando não há planos ativos."""
        
        messages = {
            SupportedLanguages.PORTUGUESE.value: "Você não tem planos ativos no momento.",
            SupportedLanguages.ENGLISH.value: "You don't have any active plans right now."
        }
        
        return messages.get(language, messages[SupportedLanguages.PORTUGUESE.value])
    
    def _get_no_recommendations_message(self, language: str) -> str:
        """Mensagem quando não há recomendações."""
        
        messages = {
            SupportedLanguages.PORTUGUESE.value: "Não foi possível gerar recomendações no momento.",
            SupportedLanguages.ENGLISH.value: "Unable to generate recommendations at the moment."
        }
        
        return messages.get(language, messages[SupportedLanguages.PORTUGUESE.value])
    
    def _get_plan_creation_error(self, language: str) -> str:
        """Mensagem de erro na criação do plano."""
        
        messages = {
            SupportedLanguages.PORTUGUESE.value: "Não foi possível criar o plano. Verifique as informações e tente novamente.",
            SupportedLanguages.ENGLISH.value: "Could not create the plan. Please check the information and try again."
        }
        
        return messages.get(language, messages[SupportedLanguages.PORTUGUESE.value])
    
    def _get_general_planning_advice(self, language: str) -> str:
        """Conselho geral sobre planejamento."""
        
        advice = {
            SupportedLanguages.PORTUGUESE.value: """
📚 **Dicas de Planejamento de Estudos**

Um bom plano de estudos deve ter:
• Objetivos claros e específicos
• Divisão do tempo adequada
• Variedade de matérias
• Momentos de revisão
• Flexibilidade para ajustes

💡 **Como começar:**
1. Defina suas metas
2. Avalie o tempo disponível
3. Priorize matérias mais difíceis
4. Inclua pausas regulares
5. Acompanhe seu progresso

Quer que eu crie um plano personalizado para você?
""",
            SupportedLanguages.ENGLISH.value: """
📚 **Study Planning Tips**

A good study plan should have:
• Clear and specific objectives
• Adequate time division
• Variety of subjects
• Review moments
• Flexibility for adjustments

💡 **How to start:**
1. Define your goals
2. Assess available time
3. Prioritize harder subjects
4. Include regular breaks
5. Track your progress

Would you like me to create a personalized plan for you?
"""
        }
        
        return advice.get(language, advice[SupportedLanguages.PORTUGUESE.value])
    
    def get_user_plans(self, user_id: str) -> List[StudyPlan]:
        """Obtém planos do usuário."""
        return self.study_plans.get(user_id, [])
    
    def complete_session(self, user_id: str, plan_id: str, session_id: str) -> bool:
        """Marca uma sessão como concluída."""
        
        try:
            user_plans = self.study_plans.get(user_id, [])
            plan = next((p for p in user_plans if p.plan_id == plan_id), None)
            
            if not plan:
                return False
            
            session = next((s for s in plan.sessions if s.session_id == session_id), None)
            
            if not session:
                return False
            
            session.is_completed = True
            session.completion_date = datetime.now()
            
            # Atualizar progresso do plano
            completed_sessions = sum(1 for s in plan.sessions if s.is_completed)
            plan.progress_percentage = (completed_sessions / len(plan.sessions)) * 100
            
            return True
        
        except Exception as e:
            logger.error(f"Erro ao completar sessão: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do agente."""
        
        total_users = len(self.study_plans)
        total_plans = sum(len(plans) for plans in self.study_plans.values())
        active_plans = sum(
            len([p for p in plans if p.is_active]) 
            for plans in self.study_plans.values()
        )
        
        return {
            'total_users_with_plans': total_users,
            'total_plans_created': total_plans,
            'active_plans': active_plans,
            'config': self.config.copy(),
            'capabilities': [cap.value for cap in self.capabilities],
            'priority': self.priority,
            'service_status': 'active'
        }