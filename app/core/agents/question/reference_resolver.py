"""
Reference resolver for handling question references and related content.
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import re
import urllib.parse

logger = logging.getLogger(__name__)


class ReferenceType(Enum):
    """Types of references that can be resolved."""
    KNOWLEDGE_BASE = "knowledge_base"      # Internal knowledge base
    EXTERNAL_LINK = "external_link"        # External web links
    STUDY_MATERIAL = "study_material"      # Study materials
    VIDEO = "video"                        # Video content
    DOCUMENT = "document"                  # Document references
    PREVIOUS_QUESTION = "previous_question" # Previous questions
    RELATED_TOPIC = "related_topic"        # Related topics


@dataclass
class ResolvedReference:
    """Container for a resolved reference."""
    reference_type: ReferenceType
    title: str
    description: str
    url: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ReferenceContext:
    """Context for reference resolution."""
    question_id: str
    subject_area: List[str]
    specific_topic: str
    difficulty: str
    exam: str
    user_level: Optional[str] = None
    preferred_language: str = "pt"
    
    def get_search_terms(self) -> List[str]:
        """Get search terms from context."""
        terms = []
        
        if self.specific_topic:
            terms.append(self.specific_topic)
        
        terms.extend(self.subject_area)
        
        if self.exam:
            terms.append(self.exam)
        
        return terms


class ReferenceResolver:
    """Resolves references and finds related content for questions."""
    
    def __init__(self):
        """Initialize the reference resolver."""
        # Reference patterns for different types
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        # Known educational domains
        self.educational_domains = {
            'khan': {'domain': 'khanacademy.org', 'type': ReferenceType.VIDEO},
            'youtube': {'domain': 'youtube.com', 'type': ReferenceType.VIDEO},
            'wikipedia': {'domain': 'wikipedia.org', 'type': ReferenceType.KNOWLEDGE_BASE},
            'brasilescola': {'domain': 'brasilescola.uol.com.br', 'type': ReferenceType.STUDY_MATERIAL},
            'mundoeducacao': {'domain': 'mundoeducacao.uol.com.br', 'type': ReferenceType.STUDY_MATERIAL},
            'infoescola': {'domain': 'infoescola.com', 'type': ReferenceType.STUDY_MATERIAL},
        }
        
        # Subject-specific reference maps
        self.subject_references = {
            'Matemática': {
                'sites': ['wolfram.com', 'geogebra.org', 'mathway.com'],
                'topics': ['álgebra', 'geometria', 'trigonometria', 'cálculo', 'estatística']
            },
            'Física': {
                'sites': ['phet.colorado.edu', 'physicsclassroom.com'],
                'topics': ['mecânica', 'termodinâmica', 'eletromagnetismo', 'óptica', 'ondulatória']
            },
            'Química': {
                'sites': ['ptable.com', 'chemspider.com'],
                'topics': ['orgânica', 'inorgânica', 'físico-química', 'bioquímica']
            },
            'Biologia': {
                'sites': ['nih.gov', 'ncbi.nlm.nih.gov'],
                'topics': ['genética', 'ecologia', 'evolução', 'anatomia', 'fisiologia']
            },
            'História': {
                'sites': ['historiadomundo.com.br', 'brasilescola.uol.com.br'],
                'topics': ['brasil', 'mundo', 'medieval', 'moderna', 'contemporânea']
            },
            'Geografia': {
                'sites': ['ibge.gov.br', 'geografiaparatodos.com.br'],
                'topics': ['física', 'humana', 'econômica', 'política', 'cartografia']
            },
            'Português': {
                'sites': ['conjugacao.com.br', 'dicio.com.br'],
                'topics': ['gramática', 'literatura', 'redação', 'interpretação']
            }
        }
        
        logger.info("Reference resolver initialized")
    
    def resolve_question_references(
        self, 
        question_data: Dict[str, Any],
        context: Optional[ReferenceContext] = None
    ) -> List[ResolvedReference]:
        """
        Resolve all references for a question.
        
        Args:
            question_data: Question data from database
            context: Additional context for resolution
            
        Returns:
            List of resolved references
        """
        references = []
        
        try:
            # Create context if not provided
            if not context:
                context = self._create_context_from_question(question_data)
            
            # Resolve embedded references from question data
            embedded_refs = self._resolve_embedded_references(question_data)
            references.extend(embedded_refs)
            
            # Find subject-specific references
            subject_refs = self._find_subject_references(context)
            references.extend(subject_refs)
            
            # Find topic-specific references
            topic_refs = self._find_topic_references(context)
            references.extend(topic_refs)
            
            # Find related study materials
            study_refs = self._find_study_materials(context)
            references.extend(study_refs)
            
            # Remove duplicates and sort by relevance
            references = self._deduplicate_references(references)
            references = self._sort_by_relevance(references, context)
            
            logger.info(f"Resolved {len(references)} references for question {question_data.get('question_id', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error resolving references: {e}")
        
        return references
    
    def _create_context_from_question(self, question_data: Dict[str, Any]) -> ReferenceContext:
        """Create reference context from question data."""
        return ReferenceContext(
            question_id=question_data.get('question_id', ''),
            subject_area=question_data.get('subject_area', []),
            specific_topic=question_data.get('specific_topic', ''),
            difficulty=question_data.get('difficulty', ''),
            exam=question_data.get('exam', '')
        )
    
    def _resolve_embedded_references(self, question_data: Dict[str, Any]) -> List[ResolvedReference]:
        """Resolve references embedded in question data."""
        references = []
        
        # Check knowledge_refs field
        knowledge_refs = question_data.get('knowledge_refs', [])
        for ref_data in knowledge_refs:
            if isinstance(ref_data, dict):
                ref = self._create_reference_from_data(ref_data)
                if ref:
                    references.append(ref)
        
        # Extract URLs from text fields
        text_fields = ['statement', 'explanation']
        for field in text_fields:
            if field in question_data:
                urls = self._extract_urls(question_data[field])
                for url in urls:
                    ref = self._create_reference_from_url(url)
                    if ref:
                        references.append(ref)
        
        return references
    
    def _create_reference_from_data(self, ref_data: Dict[str, Any]) -> Optional[ResolvedReference]:
        """Create reference from structured data."""
        try:
            # Determine reference type
            ref_type = ReferenceType.KNOWLEDGE_BASE
            
            if 'href' in ref_data and ref_data['href']:
                url = ref_data['href']
                ref_type = self._determine_reference_type(url)
            else:
                url = None
            
            return ResolvedReference(
                reference_type=ref_type,
                title=ref_data.get('mention', ref_data.get('title', 'Referência')),
                description=ref_data.get('content', ref_data.get('description', '')),
                url=url,
                metadata={
                    'source': 'embedded',
                    'original_data': ref_data
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating reference from data: {e}")
            return None
    
    def _create_reference_from_url(self, url: str) -> Optional[ResolvedReference]:
        """Create reference from URL."""
        try:
            ref_type = self._determine_reference_type(url)
            
            # Extract title from URL
            parsed_url = urllib.parse.urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Try to get a better title based on domain
            title = self._get_title_from_domain(domain)
            if not title:
                title = f"Link: {domain}"
            
            return ResolvedReference(
                reference_type=ref_type,
                title=title,
                description=f"Recurso externo: {url}",
                url=url,
                metadata={
                    'source': 'extracted_url',
                    'domain': domain
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating reference from URL: {e}")
            return None
    
    def _find_subject_references(self, context: ReferenceContext) -> List[ResolvedReference]:
        """Find references specific to the subject area."""
        references = []
        
        for subject in context.subject_area:
            if subject in self.subject_references:
                subject_data = self.subject_references[subject]
                
                # Add subject-specific sites
                for site in subject_data.get('sites', []):
                    ref = ResolvedReference(
                        reference_type=ReferenceType.STUDY_MATERIAL,
                        title=f"Material de {subject}",
                        description=f"Recursos educacionais de {subject}",
                        url=f"https://{site}",
                        metadata={
                            'source': 'subject_specific',
                            'subject': subject,
                            'relevance_score': 0.8
                        }
                    )
                    references.append(ref)
        
        return references
    
    def _find_topic_references(self, context: ReferenceContext) -> List[ResolvedReference]:
        """Find references for specific topics."""
        references = []
        
        if context.specific_topic:
            # Search for topic in subject references
            for subject in context.subject_area:
                if subject in self.subject_references:
                    topics = self.subject_references[subject].get('topics', [])
                    
                    # Check if specific topic matches any known topics
                    for topic in topics:
                        if self._topics_match(context.specific_topic, topic):
                            ref = ResolvedReference(
                                reference_type=ReferenceType.RELATED_TOPIC,
                                title=f"Estudo sobre {topic}",
                                description=f"Materiais de estudo sobre {topic} em {subject}",
                                metadata={
                                    'source': 'topic_specific',
                                    'topic': topic,
                                    'subject': subject,
                                    'relevance_score': 0.9
                                }
                            )
                            references.append(ref)
        
        return references
    
    def _find_study_materials(self, context: ReferenceContext) -> List[ResolvedReference]:
        """Find general study materials."""
        references = []
        
        # Add Khan Academy references
        if context.subject_area:
            subject = context.subject_area[0].lower()
            
            # Map subjects to Khan Academy paths
            khan_paths = {
                'matemática': 'math',
                'física': 'physics',
                'química': 'chemistry',
                'biologia': 'biology',
                'história': 'world-history',
                'geografia': 'geography',
            }
            
            if subject in khan_paths:
                ref = ResolvedReference(
                    reference_type=ReferenceType.VIDEO,
                    title=f"Khan Academy - {context.subject_area[0]}",
                    description=f"Vídeo-aulas sobre {context.subject_area[0]}",
                    url=f"https://pt.khanacademy.org/subject/{khan_paths[subject]}",
                    metadata={
                        'source': 'khan_academy',
                        'subject': subject,
                        'relevance_score': 0.7
                    }
                )
                references.append(ref)
        
        # Add Brasil Escola references
        if context.exam and 'enem' in context.exam.lower():
            ref = ResolvedReference(
                reference_type=ReferenceType.STUDY_MATERIAL,
                title="Brasil Escola - ENEM",
                description="Materiais de estudo para o ENEM",
                url="https://brasilescola.uol.com.br/enem",
                metadata={
                    'source': 'brasil_escola',
                    'exam': context.exam,
                    'relevance_score': 0.8
                }
            )
            references.append(ref)
        
        return references
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text."""
        if not text:
            return []
        
        matches = self.url_pattern.findall(text)
        return list(set(matches))  # Remove duplicates
    
    def _determine_reference_type(self, url: str) -> ReferenceType:
        """Determine reference type from URL."""
        url_lower = url.lower()
        
        # Check known domains
        for domain_info in self.educational_domains.values():
            if domain_info['domain'] in url_lower:
                return domain_info['type']
        
        # Check for video platforms
        if any(video_domain in url_lower for video_domain in ['youtube.com', 'vimeo.com', 'dailymotion.com']):
            return ReferenceType.VIDEO
        
        # Check for document types
        if any(doc_ext in url_lower for doc_ext in ['.pdf', '.doc', '.docx', '.ppt', '.pptx']):
            return ReferenceType.DOCUMENT
        
        # Default to external link
        return ReferenceType.EXTERNAL_LINK
    
    def _get_title_from_domain(self, domain: str) -> Optional[str]:
        """Get friendly title from domain name."""
        domain_titles = {
            'khanacademy.org': 'Khan Academy',
            'youtube.com': 'YouTube',
            'wikipedia.org': 'Wikipedia',
            'brasilescola.uol.com.br': 'Brasil Escola',
            'mundoeducacao.uol.com.br': 'Mundo Educação',
            'infoescola.com': 'Info Escola',
            'wolfram.com': 'Wolfram',
            'geogebra.org': 'GeoGebra',
            'ibge.gov.br': 'IBGE',
        }
        
        return domain_titles.get(domain)
    
    def _topics_match(self, topic1: str, topic2: str) -> bool:
        """Check if two topics match (fuzzy matching)."""
        if not topic1 or not topic2:
            return False
        
        topic1_lower = topic1.lower().strip()
        topic2_lower = topic2.lower().strip()
        
        # Exact match
        if topic1_lower == topic2_lower:
            return True
        
        # Substring match
        if topic1_lower in topic2_lower or topic2_lower in topic1_lower:
            return True
        
        # Word-based matching
        words1 = set(topic1_lower.split())
        words2 = set(topic2_lower.split())
        
        # If they share at least one significant word
        common_words = words1.intersection(words2)
        if common_words:
            # Filter out common words
            stop_words = {'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'na', 'no', 'nas', 'nos', 'a', 'o', 'as', 'os'}
            significant_common = common_words - stop_words
            if significant_common:
                return True
        
        return False
    
    def _deduplicate_references(self, references: List[ResolvedReference]) -> List[ResolvedReference]:
        """Remove duplicate references."""
        seen_urls = set()
        seen_titles = set()
        unique_refs = []
        
        for ref in references:
            # Check URL duplication
            if ref.url:
                if ref.url in seen_urls:
                    continue
                seen_urls.add(ref.url)
            
            # Check title duplication (fuzzy)
            title_lower = ref.title.lower().strip()
            if title_lower in seen_titles:
                continue
            seen_titles.add(title_lower)
            
            unique_refs.append(ref)
        
        return unique_refs
    
    def _sort_by_relevance(
        self, 
        references: List[ResolvedReference], 
        context: ReferenceContext
    ) -> List[ResolvedReference]:
        """Sort references by relevance score."""
        
        def calculate_relevance(ref: ResolvedReference) -> float:
            score = ref.metadata.get('relevance_score', 0.5)
            
            # Boost embedded references
            if ref.metadata.get('source') == 'embedded':
                score += 0.3
            
            # Boost subject-specific references
            if ref.metadata.get('subject') in context.subject_area:
                score += 0.2
            
            # Boost exam-specific references
            if ref.metadata.get('exam') == context.exam:
                score += 0.2
            
            # Boost by reference type
            type_scores = {
                ReferenceType.KNOWLEDGE_BASE: 0.1,
                ReferenceType.STUDY_MATERIAL: 0.15,
                ReferenceType.VIDEO: 0.1,
                ReferenceType.RELATED_TOPIC: 0.2,
                ReferenceType.EXTERNAL_LINK: 0.05,
            }
            score += type_scores.get(ref.reference_type, 0)
            
            return min(score, 1.0)  # Cap at 1.0
        
        # Calculate relevance for each reference
        for ref in references:
            ref.metadata['final_relevance_score'] = calculate_relevance(ref)
        
        # Sort by relevance (descending)
        return sorted(references, key=lambda r: r.metadata['final_relevance_score'], reverse=True)
    
    def format_references_for_display(
        self, 
        references: List[ResolvedReference],
        max_references: int = 5
    ) -> str:
        """
        Format references for display in chat.
        
        Args:
            references: List of resolved references
            max_references: Maximum number of references to display
            
        Returns:
            Formatted string with references
        """
        if not references:
            return ""
        
        # Limit number of references
        display_refs = references[:max_references]
        
        # Format references
        formatted_parts = ["📚 **Materiais de Estudo Relacionados:**\n"]
        
        for i, ref in enumerate(display_refs, 1):
            # Get emoji for reference type
            type_emoji = self._get_reference_emoji(ref.reference_type)
            
            # Format reference
            if ref.url:
                ref_text = f"{type_emoji} [{ref.title}]({ref.url})"
            else:
                ref_text = f"{type_emoji} {ref.title}"
            
            if ref.description and ref.description != ref.title:
                ref_text += f" - {ref.description}"
            
            formatted_parts.append(f"{i}. {ref_text}")
        
        return '\n'.join(formatted_parts)
    
    def _get_reference_emoji(self, ref_type: ReferenceType) -> str:
        """Get emoji for reference type."""
        emoji_map = {
            ReferenceType.KNOWLEDGE_BASE: "📖",
            ReferenceType.EXTERNAL_LINK: "🔗",
            ReferenceType.STUDY_MATERIAL: "📋",
            ReferenceType.VIDEO: "🎥",
            ReferenceType.DOCUMENT: "📄",
            ReferenceType.PREVIOUS_QUESTION: "❓",
            ReferenceType.RELATED_TOPIC: "🔍",
        }
        return emoji_map.get(ref_type, "📎")
    
    def get_reference_statistics(self, references: List[ResolvedReference]) -> Dict[str, Any]:
        """Get statistics about resolved references."""
        if not references:
            return {}
        
        # Count by type
        type_counts = {}
        for ref in references:
            ref_type = ref.reference_type.value
            type_counts[ref_type] = type_counts.get(ref_type, 0) + 1
        
        # Count by source
        source_counts = {}
        for ref in references:
            source = ref.metadata.get('source', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Average relevance score
        relevance_scores = [
            ref.metadata.get('final_relevance_score', 0.5) 
            for ref in references
        ]
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        
        return {
            'total_references': len(references),
            'type_distribution': type_counts,
            'source_distribution': source_counts,
            'average_relevance': avg_relevance,
            'has_embedded_refs': any(ref.metadata.get('source') == 'embedded' for ref in references),
            'has_external_links': any(ref.url for ref in references),
        }