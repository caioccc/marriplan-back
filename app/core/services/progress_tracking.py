"""
Progress Tracking Service - Acompanha o progresso de aprendizado do usuário.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ProgressMetricType(Enum):
    """Tipos de métricas de progresso."""
    QUESTIONS_ANSWERED = "questions_answered"
    CORRECT_ANSWERS = "correct_answers"
    STUDY_TIME = "study_time"
    CONCEPTS_LEARNED = "concepts_learned"
    SUBJECTS_STUDIED = "subjects_studied"
    STREAK_DAYS = "streak_days"
    DIFFICULTY_PROGRESSION = "difficulty_progression"
    EXPLANATION_REQUESTS = "explanation_requests"


class DifficultyLevel(Enum):
    """Níveis de dificuldade."""
    BEGINNER = "beginner"
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SubjectArea(Enum):
    """Áreas de estudo."""
    MATHEMATICS = "mathematics"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    HISTORY = "history"
    GEOGRAPHY = "geography"
    PORTUGUESE = "portuguese"
    LITERATURE = "literature"
    GENERAL = "general"


@dataclass
class LearningActivity:
    """Representa uma atividade de aprendizado."""
    activity_id: str
    user_id: str
    session_id: str
    activity_type: str  # 'question', 'explanation', 'study_plan', etc.
    subject_area: str
    difficulty_level: str
    topic: str
    timestamp: datetime
    duration_seconds: int
    success: bool
    confidence_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressSnapshot:
    """Representa um snapshot do progresso do usuário."""
    user_id: str
    timestamp: datetime
    total_activities: int
    correct_percentage: float
    average_confidence: float
    study_time_minutes: int
    subjects_studied: List[str]
    current_streak: int
    level_distribution: Dict[str, int]
    recent_topics: List[str]
    performance_trend: str  # 'improving', 'stable', 'declining'


@dataclass
class LearningGoal:
    """Representa um objetivo de aprendizado."""
    goal_id: str
    user_id: str
    title: str
    description: str
    target_metric: str
    target_value: float
    current_value: float
    deadline: Optional[datetime]
    created_at: datetime
    completed_at: Optional[datetime]
    is_active: bool


class ProgressTrackingService:
    """Serviço para acompanhar o progresso de aprendizado."""
    
    def __init__(self):
        """Inicializa o serviço de acompanhamento de progresso."""
        
        # Storage simulado - em produção seria banco de dados
        self.activities_storage = {}  # user_id -> List[LearningActivity]
        self.snapshots_storage = {}   # user_id -> List[ProgressSnapshot]
        self.goals_storage = {}       # user_id -> List[LearningGoal]
        
        # Configurações
        self.config = {
            'snapshot_interval_hours': 24,
            'streak_reset_hours': 48,
            'min_session_duration': 30,  # seconds
            'confidence_threshold': 0.7,
            'max_activities_memory': 1000,
            'performance_window_days': 7
        }
        
        logger.info("Progress Tracking Service inicializado")
    
    def record_activity(self, activity: LearningActivity) -> bool:
        """Registra uma atividade de aprendizado."""
        
        try:
            user_id = activity.user_id
            
            # Inicializar storage do usuário se não existir
            if user_id not in self.activities_storage:
                self.activities_storage[user_id] = []
            
            # Adicionar atividade
            self.activities_storage[user_id].append(activity)
            
            # Limitar número de atividades armazenadas
            max_activities = self.config['max_activities_memory']
            if len(self.activities_storage[user_id]) > max_activities:
                self.activities_storage[user_id] = self.activities_storage[user_id][-max_activities:]
            
            # Verificar se precisa criar snapshot
            self._check_and_create_snapshot(user_id)
            
            logger.debug(f"Atividade registrada para usuário {user_id}: {activity.activity_type}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao registrar atividade: {e}")
            return False
    
    def get_user_progress(self, user_id: str) -> Optional[ProgressSnapshot]:
        """Obtém o progresso atual do usuário."""
        
        try:
            activities = self.activities_storage.get(user_id, [])
            
            if not activities:
                return None
            
            # Calcular métricas atuais
            now = datetime.now()
            recent_activities = [
                a for a in activities 
                if (now - a.timestamp).days <= self.config['performance_window_days']
            ]
            
            total_activities = len(recent_activities)
            if total_activities == 0:
                return None
            
            # Calcular estatísticas
            correct_count = sum(1 for a in recent_activities if a.success)
            correct_percentage = (correct_count / total_activities) * 100
            
            average_confidence = sum(a.confidence_score for a in recent_activities) / total_activities
            
            study_time_minutes = sum(a.duration_seconds for a in recent_activities) // 60
            
            subjects_studied = list(set(a.subject_area for a in recent_activities))
            
            current_streak = self._calculate_current_streak(user_id)
            
            level_distribution = self._calculate_level_distribution(recent_activities)
            
            recent_topics = list(set(a.topic for a in recent_activities[-10:]))
            
            performance_trend = self._calculate_performance_trend(user_id)
            
            snapshot = ProgressSnapshot(
                user_id=user_id,
                timestamp=now,
                total_activities=total_activities,
                correct_percentage=correct_percentage,
                average_confidence=average_confidence,
                study_time_minutes=study_time_minutes,
                subjects_studied=subjects_studied,
                current_streak=current_streak,
                level_distribution=level_distribution,
                recent_topics=recent_topics,
                performance_trend=performance_trend
            )
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Erro ao obter progresso do usuário {user_id}: {e}")
            return None
    
    def get_detailed_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Obtém analytics detalhados do usuário."""
        
        try:
            activities = self.activities_storage.get(user_id, [])
            
            if not activities:
                return {'status': 'no_data'}
            
            # Filtrar atividades do período
            cutoff_date = datetime.now() - timedelta(days=days)
            period_activities = [a for a in activities if a.timestamp >= cutoff_date]
            
            if not period_activities:
                return {'status': 'no_recent_data'}
            
            # Analytics por dia
            daily_stats = self._calculate_daily_stats(period_activities, days)
            
            # Analytics por matéria
            subject_stats = self._calculate_subject_stats(period_activities)
            
            # Analytics por dificuldade
            difficulty_stats = self._calculate_difficulty_stats(period_activities)
            
            # Tendências de performance
            performance_trends = self._calculate_performance_trends(period_activities)
            
            # Recomendações
            recommendations = self._generate_recommendations(user_id, period_activities)
            
            return {
                'status': 'success',
                'period_days': days,
                'total_activities': len(period_activities),
                'daily_stats': daily_stats,
                'subject_stats': subject_stats,
                'difficulty_stats': difficulty_stats,
                'performance_trends': performance_trends,
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar analytics para usuário {user_id}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def set_learning_goal(self, goal: LearningGoal) -> bool:
        """Define um objetivo de aprendizado."""
        
        try:
            user_id = goal.user_id
            
            if user_id not in self.goals_storage:
                self.goals_storage[user_id] = []
            
            self.goals_storage[user_id].append(goal)
            
            logger.info(f"Objetivo definido para usuário {user_id}: {goal.title}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao definir objetivo: {e}")
            return False
    
    def update_goal_progress(self, user_id: str, goal_id: str) -> bool:
        """Atualiza o progresso de um objetivo."""
        
        try:
            goals = self.goals_storage.get(user_id, [])
            goal = next((g for g in goals if g.goal_id == goal_id), None)
            
            if not goal or not goal.is_active:
                return False
            
            # Calcular valor atual baseado no tipo de métrica
            current_value = self._calculate_goal_current_value(user_id, goal.target_metric)
            goal.current_value = current_value
            
            # Verificar se objetivo foi completado
            if current_value >= goal.target_value and not goal.completed_at:
                goal.completed_at = datetime.now()
                goal.is_active = False
                logger.info(f"Objetivo completado: {goal.title}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar progresso do objetivo: {e}")
            return False
    
    def get_user_goals(self, user_id: str, active_only: bool = False) -> List[LearningGoal]:
        """Obtém objetivos do usuário."""
        
        goals = self.goals_storage.get(user_id, [])
        
        if active_only:
            return [g for g in goals if g.is_active]
        
        return goals
    
    def _check_and_create_snapshot(self, user_id: str):
        """Verifica se deve criar um novo snapshot."""
        
        try:
            snapshots = self.snapshots_storage.get(user_id, [])
            
            # Criar snapshot se não há nenhum ou se passou o intervalo
            should_create = False
            
            if not snapshots:
                should_create = True
            else:
                last_snapshot = snapshots[-1]
                hours_since_last = (datetime.now() - last_snapshot.timestamp).total_seconds() / 3600
                
                if hours_since_last >= self.config['snapshot_interval_hours']:
                    should_create = True
            
            if should_create:
                snapshot = self.get_user_progress(user_id)
                if snapshot:
                    if user_id not in self.snapshots_storage:
                        self.snapshots_storage[user_id] = []
                    
                    self.snapshots_storage[user_id].append(snapshot)
                    
                    # Limitar número de snapshots
                    if len(self.snapshots_storage[user_id]) > 100:
                        self.snapshots_storage[user_id] = self.snapshots_storage[user_id][-100:]
                    
                    logger.debug(f"Snapshot criado para usuário {user_id}")
        
        except Exception as e:
            logger.error(f"Erro ao criar snapshot: {e}")
    
    def _calculate_current_streak(self, user_id: str) -> int:
        """Calcula a sequência atual de dias estudando."""
        
        try:
            activities = self.activities_storage.get(user_id, [])
            
            if not activities:
                return 0
            
            # Ordenar atividades por data
            sorted_activities = sorted(activities, key=lambda a: a.timestamp, reverse=True)
            
            # Verificar dias únicos de estudo
            study_dates = []
            for activity in sorted_activities:
                date = activity.timestamp.date()
                if date not in study_dates:
                    study_dates.append(date)
            
            # Calcular streak
            streak = 0
            today = datetime.now().date()
            
            for i, date in enumerate(study_dates):
                expected_date = today - timedelta(days=i)
                
                if date == expected_date:
                    streak += 1
                else:
                    break
            
            return streak
            
        except Exception as e:
            logger.error(f"Erro ao calcular streak: {e}")
            return 0
    
    def _calculate_level_distribution(self, activities: List[LearningActivity]) -> Dict[str, int]:
        """Calcula distribuição por nível de dificuldade."""
        
        distribution = {}
        
        for activity in activities:
            level = activity.difficulty_level
            distribution[level] = distribution.get(level, 0) + 1
        
        return distribution
    
    def _calculate_performance_trend(self, user_id: str) -> str:
        """Calcula tendência de performance."""
        
        try:
            activities = self.activities_storage.get(user_id, [])
            
            if len(activities) < 10:
                return 'insufficient_data'
            
            # Dividir atividades em duas metades
            mid_point = len(activities) // 2
            first_half = activities[:mid_point]
            second_half = activities[mid_point:]
            
            # Calcular performance de cada metade
            first_performance = sum(a.success for a in first_half) / len(first_half)
            second_performance = sum(a.success for a in second_half) / len(second_half)
            
            # Determinar tendência
            diff = second_performance - first_performance
            
            if diff > 0.1:
                return 'improving'
            elif diff < -0.1:
                return 'declining'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"Erro ao calcular tendência: {e}")
            return 'unknown'
    
    def _calculate_daily_stats(self, activities: List[LearningActivity], days: int) -> List[Dict[str, Any]]:
        """Calcula estatísticas diárias."""
        
        daily_stats = []
        today = datetime.now().date()
        
        for i in range(days):
            date = today - timedelta(days=i)
            day_activities = [a for a in activities if a.timestamp.date() == date]
            
            if day_activities:
                correct_count = sum(1 for a in day_activities if a.success)
                stats = {
                    'date': date.isoformat(),
                    'total_activities': len(day_activities),
                    'correct_answers': correct_count,
                    'accuracy': (correct_count / len(day_activities)) * 100,
                    'study_time_minutes': sum(a.duration_seconds for a in day_activities) // 60,
                    'subjects': list(set(a.subject_area for a in day_activities))
                }
            else:
                stats = {
                    'date': date.isoformat(),
                    'total_activities': 0,
                    'correct_answers': 0,
                    'accuracy': 0,
                    'study_time_minutes': 0,
                    'subjects': []
                }
            
            daily_stats.append(stats)
        
        return daily_stats
    
    def _calculate_subject_stats(self, activities: List[LearningActivity]) -> Dict[str, Dict[str, Any]]:
        """Calcula estatísticas por matéria."""
        
        subject_stats = {}
        
        for activity in activities:
            subject = activity.subject_area
            
            if subject not in subject_stats:
                subject_stats[subject] = {
                    'total_activities': 0,
                    'correct_answers': 0,
                    'total_time_minutes': 0,
                    'average_confidence': 0,
                    'difficulties_studied': set()
                }
            
            stats = subject_stats[subject]
            stats['total_activities'] += 1
            if activity.success:
                stats['correct_answers'] += 1
            stats['total_time_minutes'] += activity.duration_seconds // 60
            stats['average_confidence'] += activity.confidence_score
            stats['difficulties_studied'].add(activity.difficulty_level)
        
        # Finalizar cálculos
        for subject, stats in subject_stats.items():
            if stats['total_activities'] > 0:
                stats['accuracy'] = (stats['correct_answers'] / stats['total_activities']) * 100
                stats['average_confidence'] /= stats['total_activities']
                stats['difficulties_studied'] = list(stats['difficulties_studied'])
        
        return subject_stats
    
    def _calculate_difficulty_stats(self, activities: List[LearningActivity]) -> Dict[str, Dict[str, Any]]:
        """Calcula estatísticas por dificuldade."""
        
        difficulty_stats = {}
        
        for activity in activities:
            difficulty = activity.difficulty_level
            
            if difficulty not in difficulty_stats:
                difficulty_stats[difficulty] = {
                    'total_activities': 0,
                    'correct_answers': 0,
                    'average_confidence': 0
                }
            
            stats = difficulty_stats[difficulty]
            stats['total_activities'] += 1
            if activity.success:
                stats['correct_answers'] += 1
            stats['average_confidence'] += activity.confidence_score
        
        # Finalizar cálculos
        for difficulty, stats in difficulty_stats.items():
            if stats['total_activities'] > 0:
                stats['accuracy'] = (stats['correct_answers'] / stats['total_activities']) * 100
                stats['average_confidence'] /= stats['total_activities']
        
        return difficulty_stats
    
    def _calculate_performance_trends(self, activities: List[LearningActivity]) -> Dict[str, Any]:
        """Calcula tendências de performance."""
        
        if len(activities) < 5:
            return {'status': 'insufficient_data'}
        
        # Agrupar atividades em períodos
        sorted_activities = sorted(activities, key=lambda a: a.timestamp)
        
        # Calcular tendência de acurácia
        period_size = max(len(sorted_activities) // 5, 1)
        periods = []
        
        for i in range(0, len(sorted_activities), period_size):
            period_activities = sorted_activities[i:i + period_size]
            if period_activities:
                accuracy = sum(a.success for a in period_activities) / len(period_activities)
                confidence = sum(a.confidence_score for a in period_activities) / len(period_activities)
                periods.append({
                    'accuracy': accuracy,
                    'confidence': confidence,
                    'count': len(period_activities)
                })
        
        return {
            'status': 'success',
            'periods': periods,
            'overall_trend': self._analyze_trend(periods)
        }
    
    def _analyze_trend(self, periods: List[Dict[str, float]]) -> str:
        """Analisa tendência geral dos períodos."""
        
        if len(periods) < 2:
            return 'insufficient_data'
        
        # Calcular correlação simples
        accuracies = [p['accuracy'] for p in periods]
        
        # Verificar se há tendência crescente/decrescente
        increasing = sum(1 for i in range(1, len(accuracies)) if accuracies[i] > accuracies[i-1])
        decreasing = sum(1 for i in range(1, len(accuracies)) if accuracies[i] < accuracies[i-1])
        
        if increasing > decreasing * 1.5:
            return 'improving'
        elif decreasing > increasing * 1.5:
            return 'declining'
        else:
            return 'stable'
    
    def _generate_recommendations(self, user_id: str, activities: List[LearningActivity]) -> List[str]:
        """Gera recomendações baseadas no progresso."""
        
        recommendations = []
        
        if not activities:
            return ["Comece estudando para construir seu histórico de progresso!"]
        
        # Analisar performance por matéria
        subject_stats = self._calculate_subject_stats(activities)
        
        # Recomendar matérias com baixa performance
        weak_subjects = []
        for subject, stats in subject_stats.items():
            if stats['accuracy'] < 60:
                weak_subjects.append(subject)
        
        if weak_subjects:
            recommendations.append(f"Considere revisar: {', '.join(weak_subjects[:3])}")
        
        # Analisar streak
        streak = self._calculate_current_streak(user_id)
        if streak < 3:
            recommendations.append("Tente manter uma sequência de estudos diários!")
        elif streak >= 7:
            recommendations.append("Parabéns pelo streak! Continue assim!")
        
        # Analisar distribuição de dificuldade
        difficulty_stats = self._calculate_difficulty_stats(activities)
        total_activities = sum(stats['total_activities'] for stats in difficulty_stats.values())
        
        if total_activities > 0:
            basic_percentage = difficulty_stats.get('basic', {}).get('total_activities', 0) / total_activities
            
            if basic_percentage > 0.8:
                recommendations.append("Que tal tentar questões mais desafiadoras?")
            elif basic_percentage < 0.2:
                recommendations.append("Considere revisar conceitos básicos para fortalecer a base.")
        
        # Recomendar baseado no tempo de estudo
        total_time = sum(a.duration_seconds for a in activities) // 60
        if total_time < 30:
            recommendations.append("Tente dedicar mais tempo aos estudos - mesmo 15 minutos diários fazem diferença!")
        
        return recommendations[:5]  # Máximo 5 recomendações
    
    def _calculate_goal_current_value(self, user_id: str, metric_type: str) -> float:
        """Calcula valor atual de uma métrica para objetivo."""
        
        activities = self.activities_storage.get(user_id, [])
        
        if metric_type == ProgressMetricType.QUESTIONS_ANSWERED.value:
            return len([a for a in activities if a.activity_type == 'question'])
        
        elif metric_type == ProgressMetricType.CORRECT_ANSWERS.value:
            return len([a for a in activities if a.activity_type == 'question' and a.success])
        
        elif metric_type == ProgressMetricType.STUDY_TIME.value:
            return sum(a.duration_seconds for a in activities) / 3600  # hours
        
        elif metric_type == ProgressMetricType.STREAK_DAYS.value:
            return self._calculate_current_streak(user_id)
        
        elif metric_type == ProgressMetricType.SUBJECTS_STUDIED.value:
            return len(set(a.subject_area for a in activities))
        
        else:
            return 0.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do serviço."""
        
        total_users = len(self.activities_storage)
        total_activities = sum(len(activities) for activities in self.activities_storage.values())
        total_goals = sum(len(goals) for goals in self.goals_storage.values())
        
        return {
            'total_users_tracked': total_users,
            'total_activities': total_activities,
            'total_goals': total_goals,
            'config': self.config.copy(),
            'service_status': 'active'
        }