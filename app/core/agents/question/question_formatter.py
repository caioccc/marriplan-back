"""
Question formatter for presenting questions in different formats.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import html

logger = logging.getLogger(__name__)


class QuestionFormat(Enum):
    """Different formats for question presentation."""
    CHAT_MARKDOWN = "chat_markdown"      # Rich markdown for chat
    PLAIN_TEXT = "plain_text"            # Simple text format
    HTML = "html"                        # HTML format
    STRUCTURED = "structured"            # Structured data format


@dataclass
class FormattedQuestion:
    """Container for formatted question data."""
    content: str
    format_type: QuestionFormat
    metadata: Dict[str, Any]
    images: List[Dict[str, Any]]
    references: List[Dict[str, Any]]
    
    def __str__(self) -> str:
        return self.content


class QuestionFormatter:
    """Formats questions for different presentation contexts."""
    
    def __init__(self):
        """Initialize the question formatter."""
        self.format_handlers = {
            QuestionFormat.CHAT_MARKDOWN: self._format_chat_markdown,
            QuestionFormat.PLAIN_TEXT: self._format_plain_text,
            QuestionFormat.HTML: self._format_html,
            QuestionFormat.STRUCTURED: self._format_structured,
        }
        logger.info("Question formatter initialized")
    
    def format_question(
        self, 
        question_data: Dict[str, Any], 
        format_type: QuestionFormat = QuestionFormat.CHAT_MARKDOWN,
        context: Optional[Dict[str, Any]] = None
    ) -> FormattedQuestion:
        """
        Format a question according to the specified format.
        
        Args:
            question_data: Raw question data from MongoDB
            format_type: Desired output format
            context: Additional context for formatting
            
        Returns:
            FormattedQuestion with formatted content
        """
        try:
            # Validate question data
            if not self._validate_question_data(question_data):
                raise ValueError("Invalid question data structure")
            
            # Get format handler
            handler = self.format_handlers.get(format_type)
            if not handler:
                raise ValueError(f"Unsupported format type: {format_type}")
            
            # Format question
            formatted_content = handler(question_data, context or {})
            
            # Extract metadata
            metadata = self._extract_metadata(question_data)
            
            # Extract images
            images = self._extract_images(question_data)
            
            # Extract references
            references = self._extract_references(question_data)
            
            return FormattedQuestion(
                content=formatted_content,
                format_type=format_type,
                metadata=metadata,
                images=images,
                references=references
            )
            
        except Exception as e:
            logger.error(f"Error formatting question: {e}")
            # Return minimal formatted question on error
            return FormattedQuestion(
                content=self._format_error_fallback(question_data),
                format_type=format_type,
                metadata={},
                images=[],
                references=[]
            )
    
    def _validate_question_data(self, question_data: Dict[str, Any]) -> bool:
        """Validate that question data has required fields."""
        required_fields = ['question_id', 'statement', 'choices']
        return all(field in question_data for field in required_fields)
    
    def _format_chat_markdown(self, question_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Format question for chat display with rich markdown."""
        
        # Header with exam and subject info
        header_parts = []
        
        if question_data.get('exam'):
            exam_emoji = self._get_exam_emoji(question_data['exam'])
            header_parts.append(f"{exam_emoji} **{question_data['exam']}**")
        
        if question_data.get('subject_area'):
            subject = ', '.join(question_data['subject_area']) if isinstance(question_data['subject_area'], list) else question_data['subject_area']
            header_parts.append(f"📚 {subject}")
        
        header = ' - '.join(header_parts) if header_parts else "📝 **Questão**"
        
        # Topic and difficulty
        metadata_parts = []
        
        if question_data.get('specific_topic'):
            metadata_parts.append(f"📍 **Tópico:** {question_data['specific_topic']}")
        
        if question_data.get('difficulty'):
            difficulty_emoji = self._get_difficulty_emoji(question_data['difficulty'])
            metadata_parts.append(f"{difficulty_emoji} **Dificuldade:** {question_data['difficulty']}")
        
        if question_data.get('year'):
            metadata_parts.append(f"📅 **Ano:** {question_data['year']}")
        
        metadata_line = '\n'.join(metadata_parts) if metadata_parts else ""
        
        # Question statement
        statement = question_data['statement'].strip()
        statement = self._clean_html(statement)
        
        # Image placeholders
        image_text = ""
        if question_data.get('images'):
            image_count = len(question_data['images'])
            if image_count == 1:
                image_text = "\n🖼️ *Esta questão contém uma imagem*\n"
            else:
                image_text = f"\n🖼️ *Esta questão contém {image_count} imagens*\n"
        
        # Choices
        choices_text = "\n**Alternativas:**\n"
        choices = question_data['choices']
        
        for letter in ['A', 'B', 'C', 'D', 'E']:
            if letter in choices:
                choice_text = choices[letter].strip()
                choice_text = self._clean_html(choice_text)
                choices_text += f"**{letter})** {choice_text}\n"
        
        # Instructions
        instructions = "\n💡 **Digite a letra da alternativa correta (A, B, C, D ou E)**"
        
        # Build final content
        content_parts = [header]
        
        if metadata_line:
            content_parts.append(metadata_line)
        
        content_parts.extend([
            "",  # Empty line
            f"**Enunciado:**\n{statement}",
            image_text,
            choices_text.rstrip(),
            instructions
        ])
        
        return '\n'.join(filter(None, content_parts))
    
    def _format_plain_text(self, question_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Format question as plain text."""
        
        # Header
        header_parts = []
        if question_data.get('exam'):
            header_parts.append(question_data['exam'])
        if question_data.get('subject_area'):
            subject = ', '.join(question_data['subject_area']) if isinstance(question_data['subject_area'], list) else question_data['subject_area']
            header_parts.append(subject)
        
        header = ' - '.join(header_parts) if header_parts else "Questão"
        
        # Metadata
        metadata_parts = []
        if question_data.get('specific_topic'):
            metadata_parts.append(f"Tópico: {question_data['specific_topic']}")
        if question_data.get('difficulty'):
            metadata_parts.append(f"Dificuldade: {question_data['difficulty']}")
        if question_data.get('year'):
            metadata_parts.append(f"Ano: {question_data['year']}")
        
        metadata_line = ' | '.join(metadata_parts)
        
        # Statement
        statement = self._clean_html(question_data['statement'].strip())
        
        # Images note
        image_note = ""
        if question_data.get('images'):
            count = len(question_data['images'])
            image_note = f"\n[Esta questão contém {count} imagem(ns)]\n"
        
        # Choices
        choices_text = "\nAlternativas:\n"
        choices = question_data['choices']
        
        for letter in ['A', 'B', 'C', 'D', 'E']:
            if letter in choices:
                choice_text = self._clean_html(choices[letter].strip())
                choices_text += f"{letter}) {choice_text}\n"
        
        # Build content
        content_parts = [
            header,
            metadata_line,
            "",
            f"Enunciado:\n{statement}",
            image_note,
            choices_text.rstrip(),
            "\nDigite a letra da alternativa correta:"
        ]
        
        return '\n'.join(filter(None, content_parts))
    
    def _format_html(self, question_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Format question as HTML."""
        
        # Use statement_html if available, otherwise convert statement
        statement_html = question_data.get('statement_html', question_data['statement'])
        
        # Header
        header_parts = []
        if question_data.get('exam'):
            header_parts.append(f"<strong>{question_data['exam']}</strong>")
        if question_data.get('subject_area'):
            subject = ', '.join(question_data['subject_area']) if isinstance(question_data['subject_area'], list) else question_data['subject_area']
            header_parts.append(subject)
        
        header = ' - '.join(header_parts) if header_parts else "Questão"
        
        # Metadata
        metadata_html = ""
        metadata_parts = []
        if question_data.get('specific_topic'):
            metadata_parts.append(f"<strong>Tópico:</strong> {question_data['specific_topic']}")
        if question_data.get('difficulty'):
            metadata_parts.append(f"<strong>Dificuldade:</strong> {question_data['difficulty']}")
        if question_data.get('year'):
            metadata_parts.append(f"<strong>Ano:</strong> {question_data['year']}")
        
        if metadata_parts:
            metadata_html = f"<p>{' | '.join(metadata_parts)}</p>"
        
        # Images
        images_html = ""
        if question_data.get('images'):
            images_html = "<div class=\"question-images\">"
            for img in question_data['images']:
                if 'url' in img:
                    alt_text = img.get('alt', 'Imagem da questão')
                    images_html += f"<img src=\"{img['url']}\" alt=\"{html.escape(alt_text)}\" class=\"question-image\" />"
            images_html += "</div>"
        
        # Choices
        choices_html = "<ol type=\"A\" class=\"question-choices\">"
        choices = question_data['choices']
        
        for letter in ['A', 'B', 'C', 'D', 'E']:
            if letter in choices:
                choice_text = choices[letter].strip()
                choices_html += f"<li value=\"{ord(letter) - ord('A') + 1}\">{choice_text}</li>"
        
        choices_html += "</ol>"
        
        # Build final HTML
        html_content = f"""
        <div class="question-container">
            <div class="question-header">
                <h3>{header}</h3>
                {metadata_html}
            </div>
            <div class="question-statement">
                <h4>Enunciado:</h4>
                {statement_html}
            </div>
            {images_html}
            <div class="question-choices">
                <h4>Alternativas:</h4>
                {choices_html}
            </div>
            <div class="question-instructions">
                <p><em>Selecione a alternativa correta.</em></p>
            </div>
        </div>
        """
        
        return html_content.strip()
    
    def _format_structured(self, question_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Format question as structured data (JSON-like)."""
        import json
        
        # Build structured representation
        structured_data = {
            'question_id': question_data.get('question_id'),
            'exam': question_data.get('exam'),
            'subject_area': question_data.get('subject_area'),
            'specific_topic': question_data.get('specific_topic'),
            'difficulty': question_data.get('difficulty'),
            'year': question_data.get('year'),
            'statement': self._clean_html(question_data['statement']),
            'choices': question_data['choices'],
            'images': question_data.get('images', []),
            'correct_choice': question_data.get('correct_choice'),
            'explanation': question_data.get('explanation'),
            'knowledge_refs': question_data.get('knowledge_refs', [])
        }
        
        return json.dumps(structured_data, indent=2, ensure_ascii=False)
    
    def _format_error_fallback(self, question_data: Dict[str, Any]) -> str:
        """Fallback format when formatting fails."""
        statement = question_data.get('statement', 'Questão não disponível')
        choices = question_data.get('choices', {})
        
        content = f"Questão:\n{statement}\n\nAlternativas:\n"
        for letter, choice in choices.items():
            content += f"{letter}) {choice}\n"
        
        return content
    
    def _extract_metadata(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from question data."""
        return {
            'question_id': question_data.get('question_id'),
            'exam': question_data.get('exam'),
            'subject_area': question_data.get('subject_area'),
            'specific_topic': question_data.get('specific_topic'),
            'difficulty': question_data.get('difficulty'),
            'year': question_data.get('year'),
            'correct_choice': question_data.get('correct_choice'),
            'source_file': question_data.get('source_file'),
        }
    
    def _extract_images(self, question_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract image information from question data."""
        return question_data.get('images', [])
    
    def _extract_references(self, question_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract knowledge references from question data."""
        return question_data.get('knowledge_refs', [])
    
    def _clean_html(self, text: str) -> str:
        """Clean HTML tags from text."""
        if not text:
            return ""
        
        # Simple HTML tag removal (can be enhanced with proper HTML parser)
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _get_exam_emoji(self, exam: str) -> str:
        """Get emoji for exam type."""
        exam_lower = exam.lower()
        if 'enem' in exam_lower:
            return '🎓'
        elif 'vestibular' in exam_lower:
            return '🏛️'
        elif 'concurso' in exam_lower:
            return '📋'
        else:
            return '📝'
    
    def _get_difficulty_emoji(self, difficulty: str) -> str:
        """Get emoji for difficulty level."""
        difficulty_lower = difficulty.lower()
        if 'fácil' in difficulty_lower or 'easy' in difficulty_lower:
            return '🟢'
        elif 'médio' in difficulty_lower or 'medium' in difficulty_lower:
            return '🟡'
        elif 'difícil' in difficulty_lower or 'hard' in difficulty_lower:
            return '🔴'
        else:
            return '⭐'
    
    def format_answer_feedback(
        self, 
        user_answer: str, 
        correct_answer: str, 
        is_correct: bool,
        explanation: Optional[Dict[str, Any]] = None,
        time_spent: Optional[int] = None
    ) -> str:
        """
        Format feedback after user answers a question.
        
        Args:
            user_answer: User's selected answer
            correct_answer: Correct answer
            is_correct: Whether user was correct
            explanation: Explanation data
            time_spent: Time spent in seconds
            
        Returns:
            Formatted feedback string
        """
        
        # Result emoji and message
        if is_correct:
            result_emoji = "✅"
            result_message = "**Parabéns! Resposta correta!**"
        else:
            result_emoji = "❌"
            result_message = "**Resposta incorreta.**"
        
        # Basic feedback
        feedback_parts = [
            f"{result_emoji} {result_message}",
            f"Sua resposta: **{user_answer}**",
            f"Resposta correta: **{correct_answer}**"
        ]
        
        # Time information
        if time_spent is not None:
            time_text = self._format_time_spent(time_spent)
            feedback_parts.append(f"⏱️ Tempo: {time_text}")
        
        # Explanation
        if explanation:
            explanation_text = self._format_explanation(explanation)
            if explanation_text:
                feedback_parts.extend(["", "📖 **Explicação:**", explanation_text])
        
        return '\n'.join(feedback_parts)
    
    def format_hint(self, question_data: Dict[str, Any], hint_number: int) -> Optional[str]:
        """
        Format a hint for the question.
        
        Args:
            question_data: Question data
            hint_number: Which hint to show (1, 2, 3...)
            
        Returns:
            Formatted hint or None if no hint available
        """
        hints = question_data.get('hints', [])
        
        if hint_number <= len(hints):
            hint_text = hints[hint_number - 1]
            return f"💡 **Dica {hint_number}:** {hint_text}"
        
        # Generate generic hints based on question type
        if hint_number == 1:
            return "💡 **Dica 1:** Leia atentamente o enunciado e identifique as informações-chave."
        elif hint_number == 2:
            return "💡 **Dica 2:** Elimine as alternativas que claramente não fazem sentido."
        elif hint_number == 3:
            return "💡 **Dica 3:** Releia as alternativas restantes e compare com o enunciado."
        
        return None
    
    def _format_explanation(self, explanation: Dict[str, Any]) -> str:
        """Format explanation data."""
        if isinstance(explanation, str):
            return explanation
        
        if isinstance(explanation, dict):
            # Try different fields that might contain explanation
            for field in ['text', 'content', 'explanation', 'description']:
                if field in explanation and explanation[field]:
                    return str(explanation[field])
        
        return ""
    
    def _format_time_spent(self, seconds: int) -> str:
        """Format time spent in a readable way."""
        if seconds < 60:
            return f"{seconds} segundo{'s' if seconds != 1 else ''}"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds == 0:
                return f"{minutes} minuto{'s' if minutes != 1 else ''}"
            else:
                return f"{minutes}m {remaining_seconds}s"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            return f"{hours}h {remaining_minutes}m"