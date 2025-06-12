import glob
import json
import logging
import os
import hashlib
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class QuestionExtractor:
    def __init__(self, base_path: str = 'app/data/raw'):
        self.base_path = base_path

    def _generate_question_id(self, statement: str, choices: Dict[str, str]) -> str:
        """Gera ID único baseado no SHA1 do statement + choices"""
        # Cria string concatenada do statement + choices ordenadas
        choices_str = ''.join([f"{k}:{v}" for k, v in sorted(choices.items())])
        content = f"{statement}{choices_str}"
        
        # Gera SHA1
        sha1_hash = hashlib.sha1(content.encode('utf-8')).hexdigest()
        return sha1_hash[:12]  # Usa os primeiros 12 caracteres

    def _update_image_ids(self, question_id: str, images: List[Dict]) -> List[Dict]:
        """Atualiza IDs das imagens para usar o padrão question_id_image_N"""
        updated_images = []
        for i, img in enumerate(images, 1):
            updated_img = img.copy()
            updated_img['image_id'] = f"{question_id}_image_{i}"
            updated_images.append(updated_img)
        return updated_images

    def extract_all_questions(self) -> List[Dict[str, Any]]:
        """Extrai todas as questões dos arquivos JSON"""
        all_questions = []
        pattern = os.path.join(self.base_path, '**/*.json')

        for filepath in glob.glob(pattern, recursive=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if 'questions' in data and 'metadata' in data:
                    questions = data['questions']
                    metadata = data['metadata']
                    
                    # Extrai informações dos metadados
                    exam_info = {
                        'exam': metadata.get('exam', ''),
                        'year': metadata.get('year', None),
                        'day': metadata.get('day', None),
                        'retake': metadata.get('retake', False),
                        'instructions': metadata.get('instructions', '')
                    }
                    
                    # Processa cada questão
                    for q in questions:
                        # Gera novo ID baseado em SHA1
                        new_id = self._generate_question_id(
                            q.get('statement', ''), 
                            q.get('choices', {})
                        )
                        
                        # Atualiza question_id
                        original_id = q.get('question_id', '')
                        q['original_question_id'] = original_id
                        q['question_id'] = new_id
                        
                        # Atualiza image_ids se existirem
                        if 'images' in q and q['images']:
                            q['images'] = self._update_image_ids(new_id, q['images'])
                        
                        # Adiciona metadados da prova
                        q['_source_file'] = filepath
                        q['_exam_metadata'] = exam_info
                        
                        # Adiciona campos individuais para facilitar acesso
                        q['exam'] = exam_info['exam']
                        q['year'] = exam_info['year'] if exam_info['year'] else None
                        q['day'] = exam_info['day']
                        q['retake'] = exam_info['retake']
                        
                        all_questions.append(q)

                    logger.info(f"Extraídas {len(questions)} questões de {filepath}")

            except Exception as e:
                logger.error(f"Erro ao processar {filepath}: {e}")

        return all_questions
