"""
Recommendation Engine - Sistema de recomendações inteligentes para estudos.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import random
import math

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Tipos de recomendações."""
    QUESTION = "question"
    CONCEPT = "concept"
    STUDY_PLAN = "study_plan"
    REVIEW = "review"
    PRACTICE = "practice"
    DIFFICULTY_ADJUSTMENT = "difficulty_adjustment"
    SUBJECT_EXPLORATION = "subject_exploration"
    STUDY_TECHNIQUE = "study_technique"


class RecommendationPriority(Enum):
    """Prioridade das recomendações."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class UserProfile:
    """Perfil do usuário para recomendações."""
    user_id: str
    learning_style: str  # 'visual', 'auditory', 'kinesthetic', 'mixed'
    preferred_difficulty: str
    strong_subjects: List[str]
    weak_subjects: List[str]
    study_goals: List[str]
    available_time_minutes: int
    performance_level: str  # 'beginner', 'intermediate', 'advanced'
    last_activity: Optional[datetime]
    total_study_time: int
    success_rate: float
    confidence_level: float


@dataclass
class Recommendation:
    """Representa uma recomendação."""
    recommendation_id: str
    user_id: str
    type: RecommendationType
    priority: RecommendationPriority
    title: str
    description: str
    content: Dict[str, Any]
    reasons: List[str]
    estimated_time_minutes: int
    difficulty_level: str
    subject_area: str
    confidence_score: float
    created_at: datetime
    expires_at: Optional[datetime]
    is_personalized: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecommendationFeedback:
    """Feedback sobre uma recomendação."""
    recommendation_id: str
    user_id: str
    rating: int  # 1-5
    was_useful: bool
    was_followed: bool
    feedback_text: Optional[str]
    timestamp: datetime


class RecommendationEngine:
    """Engine de recomendações inteligentes."""
    
    def __init__(self):
        """Inicializa o motor de recomendações."""
        
        # Storage simulado
        self.user_profiles = {}  # user_id -> UserProfile
        self.recommendations_history = {}  # user_id -> List[Recommendation]
        self.feedback_history = {}  # recommendation_id -> RecommendationFeedback
        
        # Knowledge base
        self.concept_relationships = self._build_concept_graph()
        self.difficulty_progression = self._build_difficulty_progression()
        self.study_techniques = self._load_study_techniques()
        
        # Configurações
        self.config = {
            'max_recommendations_per_request': 5,
            'recommendation_expiry_hours': 24,
            'min_confidence_threshold': 0.3,
            'personalization_weight': 0.7,
            'novelty_weight': 0.2,
            'popularity_weight': 0.1,
            'learning_rate': 0.1
        }
        
        logger.info("Recommendation Engine inicializado")
    
    def get_recommendations(
        self, 
        user_id: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Recommendation]:
        """Obtém recomendações personalizadas para o usuário."""
        
        try:
            # Obter ou criar perfil do usuário
            profile = self._get_or_create_profile(user_id)
            
            # Analisar contexto atual
            current_context = self._analyze_current_context(user_id, context)
            
            # Gerar diferentes tipos de recomendações
            recommendations = []
            
            # 1. Recomendações baseadas em performance
            performance_recs = self._generate_performance_based_recommendations(profile, current_context)
            recommendations.extend(performance_recs)
            
            # 2. Recomendações baseadas em objetivos
            goal_recs = self._generate_goal_based_recommendations(profile, current_context)
            recommendations.extend(goal_recs)
            
            # 3. Recomendações de descoberta
            discovery_recs = self._generate_discovery_recommendations(profile, current_context)
            recommendations.extend(discovery_recs)
            
            # 4. Recomendações de revisão
            review_recs = self._generate_review_recommendations(profile, current_context)
            recommendations.extend(review_recs)
            
            # 5. Recomendações de técnicas de estudo
            technique_recs = self._generate_technique_recommendations(profile, current_context)
            recommendations.extend(technique_recs)
            
            # Rankear e filtrar recomendações
            ranked_recommendations = self._rank_recommendations(recommendations, profile)
            
            # Aplicar diversidade e limites
            final_recommendations = self._apply_diversity_and_limits(ranked_recommendations)
            
            # Salvar histórico
            self._save_recommendations_history(user_id, final_recommendations)
            
            logger.info(f"Geradas {len(final_recommendations)} recomendações para usuário {user_id}")
            return final_recommendations
        
        except Exception as e:
            logger.error(f"Erro ao gerar recomendações para usuário {user_id}: {e}")
            return self._get_fallback_recommendations(user_id)
    
    def _get_or_create_profile(self, user_id: str) -> UserProfile:
        """Obtém ou cria perfil do usuário."""
        
        if user_id not in self.user_profiles:
            # Criar perfil padrão
            self.user_profiles[user_id] = UserProfile(
                user_id=user_id,
                learning_style='mixed',
                preferred_difficulty='intermediate',
                strong_subjects=[],
                weak_subjects=[],
                study_goals=[],
                available_time_minutes=60,
                performance_level='beginner',
                last_activity=None,
                total_study_time=0,
                success_rate=0.5,
                confidence_level=0.5
            )
        
        return self.user_profiles[user_id]
    
    def _analyze_current_context(self, user_id: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analisa o contexto atual do usuário."""
        
        current_context = {
            'time_of_day': datetime.now().hour,
            'day_of_week': datetime.now().weekday(),
            'available_time': context.get('available_time', 60) if context else 60,
            'current_subject': context.get('current_subject') if context else None,
            'recent_activity': context.get('recent_activity') if context else None,
            'session_duration': context.get('session_duration', 0) if context else 0,
            'mood': context.get('mood', 'neutral') if context else 'neutral'
        }
        
        return current_context
    
    def _generate_performance_based_recommendations(
        self, 
        profile: UserProfile, 
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """Gera recomendações baseadas na performance do usuário."""
        
        recommendations = []
        
        # Recomendações para matérias fracas
        for weak_subject in profile.weak_subjects[:2]:
            rec = Recommendation(
                recommendation_id=f"perf_weak_{weak_subject}_{datetime.now().timestamp()}",
                user_id=profile.user_id,
                type=RecommendationType.PRACTICE,
                priority=RecommendationPriority.HIGH,
                title=f"Fortalecer {weak_subject.title()}",
                description=f"Pratique mais {weak_subject} para melhorar sua performance nesta matéria.",
                content={
                    'subject': weak_subject,
                    'difficulty': 'basic',
                    'focus_areas': self._get_weak_areas_in_subject(profile.user_id, weak_subject),
                    'recommended_questions': 5
                },
                reasons=[f"Performance em {weak_subject} está abaixo da média"],
                estimated_time_minutes=30,
                difficulty_level='basic',
                subject_area=weak_subject,
                confidence_score=0.8,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),
                is_personalized=True
            )
            recommendations.append(rec)
        
        # Recomendação de ajuste de dificuldade
        if profile.success_rate < 0.4:
            rec = Recommendation(
                recommendation_id=f"perf_easier_{datetime.now().timestamp()}",
                user_id=profile.user_id,
                type=RecommendationType.DIFFICULTY_ADJUSTMENT,
                priority=RecommendationPriority.MEDIUM,
                title="Tentar Questões Mais Fáceis",
                description="Comece com questões mais básicas para construir confiança.",
                content={
                    'suggested_difficulty': 'basic',
                    'current_difficulty': profile.preferred_difficulty,
                    'reason': 'low_success_rate'
                },
                reasons=["Taxa de acerto está baixa", "Questões mais fáceis podem ajudar a construir confiança"],
                estimated_time_minutes=20,
                difficulty_level='basic',
                subject_area='general',
                confidence_score=0.7,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=12),
                is_personalized=True
            )
            recommendations.append(rec)
        
        elif profile.success_rate > 0.8:
            rec = Recommendation(
                recommendation_id=f"perf_harder_{datetime.now().timestamp()}",
                user_id=profile.user_id,
                type=RecommendationType.DIFFICULTY_ADJUSTMENT,
                priority=RecommendationPriority.MEDIUM,
                title="Desafio Maior",
                description="Você está indo bem! Que tal tentar questões mais desafiadoras?",
                content={
                    'suggested_difficulty': 'advanced',
                    'current_difficulty': profile.preferred_difficulty,
                    'reason': 'high_success_rate'
                },
                reasons=["Alta taxa de acerto", "Pronto para desafios maiores"],
                estimated_time_minutes=45,
                difficulty_level='advanced',
                subject_area='general',
                confidence_score=0.8,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),
                is_personalized=True
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _generate_goal_based_recommendations(
        self, 
        profile: UserProfile, 
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """Gera recomendações baseadas nos objetivos do usuário."""
        
        recommendations = []
        
        # Se não há objetivos definidos, recomendar definir
        if not profile.study_goals:
            rec = Recommendation(
                recommendation_id=f"goal_define_{datetime.now().timestamp()}",
                user_id=profile.user_id,
                type=RecommendationType.STUDY_PLAN,
                priority=RecommendationPriority.HIGH,
                title="Defina Seus Objetivos",
                description="Estabeleça metas claras para tornar seus estudos mais eficazes.",
                content={
                    'action': 'define_goals',
                    'suggested_goals': [
                        'Melhorar em uma matéria específica',
                        'Manter sequência de estudos diários',
                        'Aumentar taxa de acerto',
                        'Preparar-se para uma prova'
                    ]
                },
                reasons=["Objetivos claros aumentam a motivação", "Facilitam o acompanhamento do progresso"],
                estimated_time_minutes=10,
                difficulty_level='basic',
                subject_area='general',
                confidence_score=0.9,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=7),
                is_personalized=True
            )
            recommendations.append(rec)
        
        # Recomendações baseadas em objetivos existentes
        for goal in profile.study_goals[:2]:
            if 'streak' in goal.lower():
                rec = Recommendation(
                    recommendation_id=f"goal_streak_{datetime.now().timestamp()}",
                    user_id=profile.user_id,
                    type=RecommendationType.PRACTICE,
                    priority=RecommendationPriority.MEDIUM,
                    title="Manter Sequência de Estudos",
                    description="Continue sua sequência estudando hoje, mesmo que por pouco tempo.",
                    content={
                        'min_time': 15,
                        'suggested_activity': 'quick_review',
                        'focus': 'consistency'
                    },
                    reasons=[f"Objetivo ativo: {goal}"],
                    estimated_time_minutes=15,
                    difficulty_level='basic',
                    subject_area='general',
                    confidence_score=0.8,
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=8),
                    is_personalized=True
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _generate_discovery_recommendations(
        self, 
        profile: UserProfile, 
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """Gera recomendações de descoberta de novos conteúdos."""
        
        recommendations = []
        
        # Recomendar explorar nova matéria
        all_subjects = ['mathematics', 'physics', 'chemistry', 'biology', 'history', 'geography']
        unstudied_subjects = [s for s in all_subjects if s not in profile.strong_subjects + profile.weak_subjects]
        
        if unstudied_subjects:
            subject = random.choice(unstudied_subjects)
            rec = Recommendation(
                recommendation_id=f"discovery_{subject}_{datetime.now().timestamp()}",
                user_id=profile.user_id,
                type=RecommendationType.SUBJECT_EXPLORATION,
                priority=RecommendationPriority.LOW,
                title=f"Explore {subject.title()}",
                description=f"Que tal conhecer alguns conceitos básicos de {subject}?",
                content={
                    'subject': subject,
                    'exploration_type': 'introduction',
                    'suggested_topics': self._get_intro_topics(subject)
                },
                reasons=["Diversificar conhecimentos é sempre bom", "Pode descobrir uma nova área de interesse"],
                estimated_time_minutes=25,
                difficulty_level='basic',
                subject_area=subject,
                confidence_score=0.6,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=3),
                is_personalized=False
            )
            recommendations.append(rec)
        
        # Recomendar conceitos relacionados
        if profile.strong_subjects:
            strong_subject = random.choice(profile.strong_subjects)
            related_concepts = self._get_related_concepts(strong_subject)
            
            if related_concepts:
                concept = random.choice(related_concepts)
                rec = Recommendation(
                    recommendation_id=f"related_{concept}_{datetime.now().timestamp()}",
                    user_id=profile.user_id,
                    type=RecommendationType.CONCEPT,
                    priority=RecommendationPriority.MEDIUM,
                    title=f"Conceito Relacionado: {concept.title()}",
                    description=f"Já que você vai bem em {strong_subject}, que tal aprender sobre {concept}?",
                    content={
                        'concept': concept,
                        'base_subject': strong_subject,
                        'relationship': 'extension'
                    },
                    reasons=[f"Baseado no seu sucesso em {strong_subject}"],
                    estimated_time_minutes=20,
                    difficulty_level=profile.preferred_difficulty,
                    subject_area=strong_subject,
                    confidence_score=0.7,
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=48),
                    is_personalized=True
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _generate_review_recommendations(
        self, 
        profile: UserProfile, 
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """Gera recomendações de revisão."""
        
        recommendations = []
        
        # Recomendar revisão baseada no tempo desde última atividade
        if profile.last_activity:
            days_since_last = (datetime.now() - profile.last_activity).days
            
            if days_since_last >= 3:
                rec = Recommendation(
                    recommendation_id=f"review_general_{datetime.now().timestamp()}",
                    user_id=profile.user_id,
                    type=RecommendationType.REVIEW,
                    priority=RecommendationPriority.HIGH,
                    title="Hora de Revisar",
                    description="Faz tempo que você não estuda. Que tal uma revisão rápida?",
                    content={
                        'review_type': 'general',
                        'suggested_subjects': profile.strong_subjects[:2],
                        'review_method': 'quick_questions'
                    },
                    reasons=[f"Últimos estudos há {days_since_last} dias"],
                    estimated_time_minutes=20,
                    difficulty_level='basic',
                    subject_area='general',
                    confidence_score=0.8,
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=6),
                    is_personalized=True
                )
                recommendations.append(rec)
        
        # Revisão espaçada
        if profile.strong_subjects:
            for subject in profile.strong_subjects[:1]:
                rec = Recommendation(
                    recommendation_id=f"spaced_review_{subject}_{datetime.now().timestamp()}",
                    user_id=profile.user_id,
                    type=RecommendationType.REVIEW,
                    priority=RecommendationPriority.MEDIUM,
                    title=f"Revisão Espaçada: {subject.title()}",
                    description=f"Revise {subject} para manter o conhecimento fresco na memória.",
                    content={
                        'subject': subject,
                        'review_type': 'spaced',
                        'interval': 'weekly'
                    },
                    reasons=["Revisão espaçada melhora a retenção"],
                    estimated_time_minutes=15,
                    difficulty_level='intermediate',
                    subject_area=subject,
                    confidence_score=0.7,
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(days=1),
                    is_personalized=True
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _generate_technique_recommendations(
        self, 
        profile: UserProfile, 
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """Gera recomendações de técnicas de estudo."""
        
        recommendations = []
        
        # Recomendar técnica baseada no perfil
        suitable_techniques = self._get_suitable_techniques(profile)
        
        if suitable_techniques:
            technique = random.choice(suitable_techniques)
            rec = Recommendation(
                recommendation_id=f"technique_{technique['name']}_{datetime.now().timestamp()}",
                user_id=profile.user_id,
                type=RecommendationType.STUDY_TECHNIQUE,
                priority=RecommendationPriority.LOW,
                title=f"Técnica: {technique['name']}",
                description=technique['description'],
                content={
                    'technique': technique,
                    'instructions': technique['instructions'],
                    'benefits': technique['benefits']
                },
                reasons=["Técnicas de estudo podem melhorar sua eficiência"],
                estimated_time_minutes=technique['time_minutes'],
                difficulty_level='basic',
                subject_area='general',
                confidence_score=0.6,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=7),
                is_personalized=True
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _rank_recommendations(
        self, 
        recommendations: List[Recommendation], 
        profile: UserProfile
    ) -> List[Recommendation]:
        """Rankeia recomendações por relevância."""
        
        for rec in recommendations:
            score = 0.0
            
            # Score baseado na prioridade
            priority_scores = {
                RecommendationPriority.CRITICAL: 1.0,
                RecommendationPriority.HIGH: 0.8,
                RecommendationPriority.MEDIUM: 0.6,
                RecommendationPriority.LOW: 0.4
            }
            score += priority_scores.get(rec.priority, 0.5) * 0.4
            
            # Score baseado na personalização
            if rec.is_personalized:
                score += self.config['personalization_weight']
            
            # Score baseado na confiança
            score += rec.confidence_score * 0.3
            
            # Penalizar se o tempo estimado é muito maior que disponível
            available_time = profile.available_time_minutes
            if rec.estimated_time_minutes > available_time * 1.5:
                score *= 0.7
            
            # Boost para matérias fracas
            if rec.subject_area in profile.weak_subjects:
                score *= 1.2
            
            rec.metadata['ranking_score'] = score
        
        # Ordenar por score
        return sorted(recommendations, key=lambda r: r.metadata.get('ranking_score', 0), reverse=True)
    
    def _apply_diversity_and_limits(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """Aplica diversidade e limites às recomendações."""
        
        # Limitar número total
        max_recs = self.config['max_recommendations_per_request']
        
        # Garantir diversidade de tipos
        final_recs = []
        types_used = set()
        
        for rec in recommendations:
            if len(final_recs) >= max_recs:
                break
            
            # Preferir tipos ainda não usados
            if rec.type not in types_used or len(final_recs) < 3:
                final_recs.append(rec)
                types_used.add(rec.type)
        
        # Completar com melhores recomendações se necessário
        for rec in recommendations:
            if len(final_recs) >= max_recs:
                break
            if rec not in final_recs:
                final_recs.append(rec)
        
        return final_recs[:max_recs]
    
    def _build_concept_graph(self) -> Dict[str, List[str]]:
        """Constrói grafo de relacionamentos entre conceitos."""
        
        return {
            'algebra': ['equations', 'functions', 'polynomials'],
            'geometry': ['triangles', 'circles', 'areas'],
            'physics': ['mechanics', 'energy', 'waves'],
            'chemistry': ['atoms', 'reactions', 'molecules'],
            'biology': ['cells', 'genetics', 'evolution']
        }
    
    def _build_difficulty_progression(self) -> Dict[str, List[str]]:
        """Constrói progressão de dificuldade por matéria."""
        
        return {
            'mathematics': ['basic_arithmetic', 'algebra', 'geometry', 'calculus'],
            'physics': ['kinematics', 'dynamics', 'energy', 'waves', 'quantum'],
            'chemistry': ['atomic_structure', 'bonding', 'reactions', 'thermodynamics']
        }
    
    def _load_study_techniques(self) -> List[Dict[str, Any]]:
        """Carrega técnicas de estudo."""
        
        return [
            {
                'name': 'Pomodoro',
                'description': 'Estude por 25 minutos, depois descanse 5 minutos.',
                'instructions': ['Defina um timer para 25 minutos', 'Estude com foco total', 'Descanse 5 minutos', 'Repita'],
                'benefits': ['Mantém foco', 'Evita fadiga mental'],
                'time_minutes': 30,
                'suitable_for': ['all']
            },
            {
                'name': 'Resumos',
                'description': 'Faça resumos do que estudou para fixar o conteúdo.',
                'instructions': ['Leia o conteúdo', 'Identifique pontos principais', 'Escreva resumo próprio'],
                'benefits': ['Melhora retenção', 'Força compreensão'],
                'time_minutes': 20,
                'suitable_for': ['visual', 'mixed']
            },
            {
                'name': 'Flashcards',
                'description': 'Use cartões com perguntas e respostas para memorização.',
                'instructions': ['Crie cartões com pergunta/resposta', 'Revise regularmente', 'Foque nos erros'],
                'benefits': ['Memorização eficaz', 'Revisão rápida'],
                'time_minutes': 15,
                'suitable_for': ['visual', 'kinesthetic']
            }
        ]
    
    def _get_weak_areas_in_subject(self, user_id: str, subject: str) -> List[str]:
        """Obtém áreas fracas em uma matéria específica."""
        
        # Simulação - em produção viria do histórico do usuário
        weak_areas_map = {
            'mathematics': ['frações', 'equações', 'geometria'],
            'physics': ['cinemática', 'energia', 'ondas'],
            'chemistry': ['ligações', 'reações', 'estequiometria']
        }
        
        return weak_areas_map.get(subject, ['conceitos básicos'])
    
    def _get_intro_topics(self, subject: str) -> List[str]:
        """Obtém tópicos introdutórios de uma matéria."""
        
        intro_topics = {
            'mathematics': ['números', 'operações básicas', 'frações'],
            'physics': ['movimento', 'força', 'energia'],
            'chemistry': ['átomos', 'elementos', 'ligações'],
            'biology': ['células', 'vida', 'organismos'],
            'history': ['civilizações', 'cronologia', 'períodos'],
            'geography': ['continentes', 'clima', 'população']
        }
        
        return intro_topics.get(subject, ['conceitos básicos'])
    
    def _get_related_concepts(self, subject: str) -> List[str]:
        """Obtém conceitos relacionados a uma matéria."""
        
        return self.concept_relationships.get(subject, [])
    
    def _get_suitable_techniques(self, profile: UserProfile) -> List[Dict[str, Any]]:
        """Obtém técnicas adequadas para o perfil do usuário."""
        
        suitable = []
        
        for technique in self.study_techniques:
            suitable_for = technique.get('suitable_for', ['all'])
            
            if 'all' in suitable_for or profile.learning_style in suitable_for:
                # Verificar se o tempo é adequado
                if technique['time_minutes'] <= profile.available_time_minutes:
                    suitable.append(technique)
        
        return suitable
    
    def _save_recommendations_history(self, user_id: str, recommendations: List[Recommendation]):
        """Salva histórico de recomendações."""
        
        if user_id not in self.recommendations_history:
            self.recommendations_history[user_id] = []
        
        self.recommendations_history[user_id].extend(recommendations)
        
        # Limitar histórico
        if len(self.recommendations_history[user_id]) > 100:
            self.recommendations_history[user_id] = self.recommendations_history[user_id][-100:]
    
    def _get_fallback_recommendations(self, user_id: str) -> List[Recommendation]:
        """Obtém recomendações de fallback em caso de erro."""
        
        fallback_recs = [
            Recommendation(
                recommendation_id=f"fallback_1_{datetime.now().timestamp()}",
                user_id=user_id,
                type=RecommendationType.PRACTICE,
                priority=RecommendationPriority.MEDIUM,
                title="Pratique Questões",
                description="Resolva algumas questões para manter o ritmo de estudos.",
                content={'action': 'practice_questions', 'count': 5},
                reasons=["Prática regular é fundamental"],
                estimated_time_minutes=30,
                difficulty_level='intermediate',
                subject_area='general',
                confidence_score=0.7,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),
                is_personalized=False
            ),
            Recommendation(
                recommendation_id=f"fallback_2_{datetime.now().timestamp()}",
                user_id=user_id,
                type=RecommendationType.STUDY_TECHNIQUE,
                priority=RecommendationPriority.LOW,
                title="Técnica Pomodoro",
                description="Experimente estudar por 25 minutos com foco total.",
                content={'technique': 'pomodoro', 'duration': 25},
                reasons=["Técnica comprovada para melhorar foco"],
                estimated_time_minutes=25,
                difficulty_level='basic',
                subject_area='general',
                confidence_score=0.8,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=7),
                is_personalized=False
            )
        ]
        
        return fallback_recs
    
    def record_feedback(self, feedback: RecommendationFeedback) -> bool:
        """Registra feedback sobre uma recomendação."""
        
        try:
            self.feedback_history[feedback.recommendation_id] = feedback
            
            # Usar feedback para melhorar futuras recomendações
            self._learn_from_feedback(feedback)
            
            logger.info(f"Feedback registrado para recomendação {feedback.recommendation_id}")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao registrar feedback: {e}")
            return False
    
    def _learn_from_feedback(self, feedback: RecommendationFeedback):
        """Aprende com o feedback para melhorar recomendações futuras."""
        
        # Atualizar perfil do usuário baseado no feedback
        if feedback.user_id in self.user_profiles:
            profile = self.user_profiles[feedback.user_id]
            
            # Ajustar preferências baseado no feedback
            learning_rate = self.config['learning_rate']
            
            if feedback.was_useful and feedback.rating >= 4:
                # Reforçar características da recomendação bem avaliada
                # (Implementação simplificada)
                profile.confidence_level = min(1.0, profile.confidence_level + learning_rate * 0.1)
            
            elif feedback.rating <= 2:
                # Diminuir confiança em características mal avaliadas
                profile.confidence_level = max(0.0, profile.confidence_level - learning_rate * 0.1)
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Atualiza perfil do usuário."""
        
        try:
            profile = self._get_or_create_profile(user_id)
            
            # Atualizar campos permitidos
            allowed_fields = [
                'learning_style', 'preferred_difficulty', 'strong_subjects',
                'weak_subjects', 'study_goals', 'available_time_minutes',
                'performance_level'
            ]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(profile, field, value)
            
            logger.info(f"Perfil do usuário {user_id} atualizado")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao atualizar perfil: {e}")
            return False
    
    def get_recommendation_analytics(self, user_id: str) -> Dict[str, Any]:
        """Obtém analytics das recomendações do usuário."""
        
        try:
            recommendations = self.recommendations_history.get(user_id, [])
            
            if not recommendations:
                return {'status': 'no_data'}
            
            # Estatísticas básicas
            total_recommendations = len(recommendations)
            types_distribution = {}
            priorities_distribution = {}
            
            for rec in recommendations:
                rec_type = rec.type.value
                priority = rec.priority.value
                
                types_distribution[rec_type] = types_distribution.get(rec_type, 0) + 1
                priorities_distribution[priority] = priorities_distribution.get(priority, 0) + 1
            
            # Feedback statistics
            feedbacks = [
                self.feedback_history.get(rec.recommendation_id) 
                for rec in recommendations 
                if rec.recommendation_id in self.feedback_history
            ]
            
            feedback_stats = {}
            if feedbacks:
                avg_rating = sum(f.rating for f in feedbacks if f) / len(feedbacks)
                useful_rate = sum(1 for f in feedbacks if f and f.was_useful) / len(feedbacks)
                follow_rate = sum(1 for f in feedbacks if f and f.was_followed) / len(feedbacks)
                
                feedback_stats = {
                    'total_feedbacks': len(feedbacks),
                    'average_rating': avg_rating,
                    'useful_rate': useful_rate,
                    'follow_rate': follow_rate
                }
            
            return {
                'status': 'success',
                'total_recommendations': total_recommendations,
                'types_distribution': types_distribution,
                'priorities_distribution': priorities_distribution,
                'feedback_stats': feedback_stats,
                'generated_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Erro ao gerar analytics: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do serviço."""
        
        total_users = len(self.user_profiles)
        total_recommendations = sum(len(recs) for recs in self.recommendations_history.values())
        total_feedbacks = len(self.feedback_history)
        
        return {
            'total_users': total_users,
            'total_recommendations': total_recommendations,
            'total_feedbacks': total_feedbacks,
            'config': self.config.copy(),
            'service_status': 'active'
        }